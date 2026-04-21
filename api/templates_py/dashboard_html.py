# Auto-extraído de index.py — Fase A refactor
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Planta - Espagiria Laboratorios</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:#F5F4F0; min-height:100vh; padding:20px; }
.container { max-width:1400px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.3); overflow:hidden; }
.header { background:#2B7A78; color:white; padding:25px; text-align:center; }
.header h1 { font-size:1.8em; margin-bottom:6px; }
.tabs { display:flex; background:#f5f5f5; border-bottom:2px solid #ddd; overflow-x:auto; }
.tab-button { flex:1; padding:13px 12px; background:none; border:none; cursor:pointer; font-size:0.9em; font-weight:500; color:#666; white-space:nowrap; min-width:90px; transition:all 0.2s; }
.tab-button:hover { background:white; color:#2B7A78; }
.tab-button.active { background:white; color:#2B7A78; border-bottom:3px solid #2B7A78; }
.tab-content { display:none; padding:25px; }
.tab-content.active { display:block; }
.sub-tab-bar { display:none; background:#e8f4f3; border-bottom:2px solid #2B7A78; padding:5px 10px; gap:5px; flex-wrap:wrap; }
.sub-tab-bar.visible { display:flex; }
.sub-btn { padding:7px 18px; border:none; border-radius:6px; font-size:0.82em; font-weight:600; cursor:pointer; background:transparent; color:#2B7A78; }
.sub-btn.active { background:#2B7A78; color:white; }
.sub-btn:hover { background:rgba(43,122,120,0.18); }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:15px; margin:15px 0; }
.card { background:#2B7A78; color:white; padding:18px; border-radius:10px; text-align:center; }
.card h3 { font-size:0.85em; opacity:0.9; margin-bottom:6px; }
.card p { font-size:1.8em; font-weight:700; }
button { background:#2B7A78; color:white; border:none; padding:10px 18px; border-radius:6px; cursor:pointer; font-size:0.9em; font-weight:500; }
button:hover { opacity:0.9; }
input,select,textarea { width:100%; padding:9px; border:1px solid #ddd; border-radius:6px; font-size:0.95em; margin-top:3px; }
.form-group { margin-bottom:14px; }
label { font-weight:600; font-size:0.88em; color:#444; }
.table { width:100%; border-collapse:collapse; margin-top:12px; font-size:0.88em; }
.table th { background:#2B7A78; color:white; padding:9px 10px; text-align:left; }
.table td { padding:8px 10px; border-bottom:1px solid #eee; }
.table tr:hover { background:#f8f9ff; }
.alert-success { background:#d4edda; color:#155724; padding:10px; border-radius:6px; margin-top:8px; }
.alert-error { background:#f8d7da; color:#721c24; padding:10px; border-radius:6px; margin-top:8px; }
.chat-box { height:320px; overflow-y:auto; border:1px solid #ddd; border-radius:8px; padding:12px; margin-bottom:12px; background:#f9f9f9; }
.mp-item:hover { background:#f0f8ff !important; }
.msg { margin-bottom:10px; padding:9px 13px; border-radius:8px; max-width:85%; }
.msg.user { background:#667eea; color:white; margin-left:auto; }
.msg.bot { background:white; border:1px solid #ddd; }
h2 { color:#333; margin-bottom:12px; font-size:1.3em; }
</style>
</head>
<body>
<div id="modal-operador" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.82);z-index:9999;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:18px;padding:36px 32px;max-width:380px;width:94%;box-shadow:0 20px 60px rgba(0,0,0,0.5);text-align:center;">
    <div style="font-size:2.2em;margin-bottom:10px;">&#128100;</div>
    <h2 style="color:#2B7A78;margin-bottom:6px;font-size:1.25em;">&#191;Qui&#233;n est&#225; operando?</h2>
    <p style="color:#666;font-size:0.88em;margin-bottom:20px;">Escribe tu nombre para registrar movimientos correctamente.</p>
    <input type="text" id="oper-input" placeholder="Ej: Alejandro, Valentina..." autocomplete="off"
      style="width:100%;padding:12px 14px;border:2px solid #e2e8f0;border-radius:10px;font-size:1em;outline:none;box-sizing:border-box;margin-bottom:8px;"
      onkeydown="if(event.key==='Enter')confirmarOper()">
    <div id="oper-error" style="display:none;color:#dc3545;font-size:0.82em;margin-bottom:8px;">&#9888; Escribe tu nombre para continuar.</div>
    <button onclick="confirmarOper()" style="width:100%;background:linear-gradient(135deg,#2B7A78,#1a5c5a);color:white;border:none;border-radius:10px;padding:13px;font-size:1em;font-weight:700;cursor:pointer;margin-top:4px;">Entrar al sistema &#8594;</button>
  </div>
</div>
<div id="modal-solicitud-compra" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9996;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:32px;max-width:480px;width:95%;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <h2 style="color:#2B7A78;margin-bottom:4px;">&#128722; Solicitar Compra</h2>
    <p id="sol-mp-info" style="color:#666;font-size:0.9em;margin-bottom:18px;"></p>
    <div class="form-group"><label>Tu nombre *</label><input type="text" id="sol-nombre" placeholder="Ej: Alejandro, Catalina..."></div>
    <div class="form-group"><label>Cantidad a pedir (g) *</label><input type="number" id="sol-cantidad" placeholder="0" step="0.01" min="1" style="border:2px solid #2B7A78;"></div>
    <div class="form-group"><label>Urgencia</label><select id="sol-urgencia"><option value="Normal">Normal</option><option value="Urgente">Urgente</option><option value="Critica">Critica</option></select></div>
    <div class="form-group"><label>Observacion</label><input type="text" id="sol-obs" placeholder="Opcional"></div>
    <div id="sol-msg" style="margin-bottom:10px;"></div>
    <div style="display:flex;gap:10px;">
      <button onclick="enviarSolicitudCompra()" style="flex:1;background:#2B7A78;">&#10003; Enviar Solicitud</button>
      <button onclick="cerrarSolicitudCompra()" style="flex:1;background:#6c757d;">Cancelar</button>
    </div>
  </div>
</div>
<div id="modal-historial" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9997;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:32px;max-width:680px;width:95%;max-height:80vh;overflow-y:auto;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="color:#2B7A78;margin:0;">&#128203; Historial del Lote</h2>
      <button onclick="cerrarHistorial()" style="background:#6c757d;padding:6px 14px;">&#10005; Cerrar</button>
    </div>
    <p id="hist-lote-info" style="color:#666;font-size:0.9em;margin-bottom:16px;"></p>
    <table class="table"><thead><tr><th>Tipo</th><th>Cantidad (g)</th><th>Fecha</th><th>Observaciones</th><th>Operador</th></tr></thead>
    <tbody id="hist-lote-body"><tr><td colspan="5" style="text-align:center;color:#999;">Cargando...</td></tr></tbody></table>
  </div>
</div>
<div id="modal-ajuste" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;"><div id="modal-ajuste-body" style="background:white;border-radius:16px;padding:0;max-width:700px;width:96%;max-height:90vh;overflow-y:auto;">
  <div style="background:white;border-radius:16px;padding:28px;max-width:500px;width:96%;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
      <h2 style="color:#2B7A78;margin:0;">&#9878; Gestionar Material</h2>
      <button onclick="cerrarAjuste()" style="background:none;border:none;font-size:1.6em;cursor:pointer;color:#aaa;padding:0 4px;line-height:1;" title="Cerrar">&#10005;</button>
    </div>
    <p id="ajuste-info" style="color:#666;font-size:0.88em;margin-bottom:14px;"></p>
    <div style="border:1px solid #d0ece7;border-radius:8px;padding:14px;margin-bottom:10px;background:#f9fffe;">
      <div style="font-size:0.78em;font-weight:700;color:#2B7A78;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">&#128203; Conteo F&#237;sico</div>
      <div class="form-group"><label>Stock en sistema (g)</label><input type="number" id="ajuste-sistema" readonly style="background:#f5f5f5;color:#888;"></div>
      <div class="form-group"><label style="color:#2B7A78;font-weight:700;">Cantidad f&#237;sica real (g) *</label><input type="number" id="ajuste-fisico" placeholder="Lo que tienes f&#237;sicamente" step="0.01" min="0" style="border:2px solid #2B7A78;"></div>
      <div class="form-group"><label>Observaci&#243;n</label><input type="text" id="ajuste-obs" placeholder="Ej: Conteo del 15/04"></div>
      <div style="display:flex;gap:8px;margin-top:10px;">
        <button onclick="confirmarAjuste()" style="flex:1;background:#2B7A78;padding:8px;">&#10003; Confirmar Ajuste</button>
        <button onclick="cerrarAjuste()" style="flex:1;background:#6c757d;padding:8px;">Cancelar</button>
      </div>
      <div id="ajuste-msg" style="margin-top:8px;font-size:0.85em;"></div>
    </div>
    <div style="border:1px solid #ffeeba;border-radius:8px;padding:14px;margin-bottom:10px;background:#fffdf0;">
      <div style="font-size:0.78em;font-weight:700;color:#856404;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">&#128202; Stock M&#237;nimo</div>
      <div style="display:flex;gap:8px;align-items:flex-end;">
        <div class="form-group" style="flex:1;margin-bottom:0;"><label>Nuevo m&#237;nimo (g)</label><input type="number" id="ajuste-smin" placeholder="0" step="0.1" min="0"></div>
        <button onclick="actualizarStockMinimo()" style="background:#856404;color:white;padding:8px 14px;white-space:nowrap;border-radius:6px;">Actualizar</button>
      </div>
      <div id="ajuste-smin-msg" style="margin-top:6px;font-size:0.82em;"></div>
    </div>
    <div style="border:1px solid #d8b4fe;border-radius:8px;padding:14px;margin-bottom:10px;background:#faf5ff;">
      <div style="font-size:0.78em;font-weight:700;color:#6f42c1;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">&#9749; Consumo Manual</div>
      <div style="display:flex;gap:8px;align-items:flex-end;">
        <div class="form-group" style="flex:1;margin-bottom:0;"><label>Cantidad a consumir (g)</label><input type="number" id="ajuste-consumo" placeholder="Ej: 250" step="0.1" min="0.01"></div>
        <button onclick="registrarConsumo()" style="background:#6f42c1;color:white;padding:8px 14px;white-space:nowrap;border-radius:6px;">Registrar</button>
      </div>
      <div id="ajuste-consumo-msg" style="margin-top:6px;font-size:0.82em;"></div>
    </div>
    <div style="border:1px solid #f5c6cb;border-radius:8px;padding:12px;background:#fff8f8;">
      <div style="font-size:0.78em;font-weight:700;color:#c0392b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">&#128190; Archivar Material</div>
      <p style="font-size:0.82em;color:#888;margin-bottom:8px;">Oculta el material del cat&#225;logo activo sin eliminar su historial.</p>
      <button onclick="archivarMP()" style="background:#c0392b;color:white;padding:6px 14px;font-size:0.83em;border-radius:6px;">Archivar este material</button>
      <div id="ajuste-arch-msg" style="margin-top:6px;font-size:0.82em;"></div>
    </div>
  </div>
</div>
</div>
<div class="container">
  <div class="header" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;">
    <div><div style="display:flex;align-items:center;gap:12px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="34" height="34"><path d="M30 18 L30 38 L16 60 L64 60 L50 38 L50 18 Z" fill="none" stroke="white" stroke-width="3"/><line x1="27" y1="24" x2="53" y2="24" stroke="white" stroke-width="2.5"/><path d="M40 48 Q33 40 33 33 Q40 38 40 48Z" fill="white" opacity="0.8"/><path d="M40 48 Q47 40 47 33 Q40 38 40 48Z" fill="white" opacity="0.8"/><path d="M40 48 Q29 45 27 52 Q34 50 40 48Z" fill="white" opacity="0.6"/><path d="M40 48 Q51 45 53 52 Q46 50 40 48Z" fill="white" opacity="0.6"/></svg><div><div style="font-size:1.4em;font-weight:700;">Módulo Planta</div><div style="font-size:0.75em;letter-spacing:2px;opacity:0.8;font-weight:500;margin-top:2px;">ESPAGIRIA LABORATORIOS</div></div></div>
    <p>Espagiria Laboratorios - Control de Materias Primas</p>
    </div>
    <a href="/" style="color:rgba(255,255,255,0.75);font-size:0.82em;text-decoration:none;white-space:nowrap;">← Portal HHA</a><span id="oper-chip" style="font-size:0.78em;background:rgba(255,255,255,0.2);padding:3px 10px;border-radius:12px;color:white;margin-top:4px;display:block;"></span>
  </div>
  <div class="tabs">
    <button class="tab-button active" onclick="switchTab('dashboard',this)">&#128202; Dashboard</button>
    <button class="tab-button" onclick="switchGroup('bar-bodegaMP','stock',this)">&#128230; Bodega MP</button>
    <button class="tab-button" onclick="switchTab('empaque',this)">&#129492; Bodega MEE</button>
    <button class="tab-button" onclick="switchGroup('bar-prodHub','formulas',this)">&#127981; Producción</button>
    <button class="tab-button" onclick="switchTab('acondicionamiento',this)">&#128295; Acondicionamiento</button>
    <button class="tab-button" onclick="switchTab('liberacion',this)">&#128666; Liberación</button>
    <button class="tab-button" onclick="switchGroup('bar-calidadHub','cuarentena',this)">&#128274; Calidad</button>
    <button class="tab-button" onclick="switchTab('trazabilidad',this)">&#128269; Trazabilidad</button>
  </div>
  <div id="bar-bodegaMP" class="sub-tab-bar">
    <button class="sub-btn active" onclick="subSwitchTab('stock',this,'bar-bodegaMP')">&#128230; Inventario MP</button>
    <button class="sub-btn" onclick="subSwitchTab('ingreso',this,'bar-bodegaMP')">&#128666; Recepciones</button>
    <button class="sub-btn" onclick="subSwitchTab('abc',this,'bar-bodegaMP')">&#128200; Análisis ABC</button>
    <button class="sub-btn" onclick="subSwitchTab('alertas',this,'bar-bodegaMP')">&#9888; Alertas</button>
    <button class="sub-btn" onclick="subSwitchTab('movimientos',this,'bar-bodegaMP')">&#128203; Movimientos</button>
  </div>
  <div id="bar-prodHub" class="sub-tab-bar">
    <button class="sub-btn active" onclick="subSwitchTab('formulas',this,'bar-prodHub')">&#129514; Fórmulas</button>
    <button class="sub-btn" onclick="subSwitchTab('produccion',this,'bar-prodHub')">&#127981; Lote</button>
  </div>
  <div id="bar-calidadHub" class="sub-tab-bar">
    <button class="sub-btn active" onclick="subSwitchTab('cuarentena',this,'bar-calidadHub')">&#128274; Cuarentena</button>
    <button class="sub-btn" onclick="subSwitchTab('conteo',this,'bar-calidadHub')">&#9989; Conteo Cíclico</button>
  </div>

  <div id="dashboard" class="tab-content active">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <h2 style="margin:0;">Dashboard Ejecutivo</h2>
      <button onclick="loadDashboardCompleto();loadAcond();loadLiberaciones('');" style="padding:7px 16px;font-size:0.88em;">&#8635; Actualizar</button>
    </div>

    <!-- KPI Cards -->
    <div class="grid" style="margin-bottom:20px;">
      <div class="card"><h3>Stock Total</h3><p id="stock-total">-</p></div>
      <div class="card"><h3>Lotes en Bodega</h3><p id="materiales-count">-</p></div>
      <div class="card" id="card-alertas" style="cursor:pointer;" onclick="switchGroup('bar-bodegaMP','alertas',null)"><h3>MPs bajo Minimo</h3><p id="alertas-count" style="color:#e65100;">-</p></div>
      <div class="card"><h3>Producciones</h3><p id="producciones-count">-</p></div>
    </div>

    <!-- Alertas criticas rápidas -->
    <div id="dash-alertas-rapidas" style="display:none;background:#ffebeb;border:1px solid #cc0000;border-radius:8px;padding:12px;margin-bottom:20px;">
      <h4 style="color:#cc0000;margin-bottom:8px;">&#128308; MPs criticas — bajo stock minimo ahora</h4>
      <div id="dash-alertas-lista" style="font-size:0.88em;"></div>
    </div>

    <!-- Gráficas -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px;">
      <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
        <h4 style="margin-bottom:12px;color:#333;">&#128308; Vencimientos próximos 6 meses</h4>
        <canvas id="chart-vencimientos" height="180"></canvas>
        <p id="chart-venc-empty" style="text-align:center;color:#999;font-size:0.88em;display:none;">Sin vencimientos próximos</p>
      </div>
      <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
        <h4 style="margin-bottom:12px;color:#333;">&#128230; Top 5 MPs por Stock</h4>
        <canvas id="chart-top-stock" height="180"></canvas>
        <p id="chart-stock-empty" style="text-align:center;color:#999;font-size:0.88em;display:none;">Sin datos de stock</p>
      </div>
    </div>

    <!-- Estado de lotes -->
    <div style="background:white;border:1px solid #dde;border-radius:8px;padding:16px;">
      <h4 style="margin-bottom:12px;color:#333;">Estado general de lotes</h4>
      <div style="display:flex;gap:15px;flex-wrap:wrap;" id="dash-estados">
        <div style="text-align:center;padding:10px 20px;background:#ffebeb;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#cc0000;" id="dash-vencidos">-</div>
          <div style="font-size:0.82em;color:#888;">Vencidos</div>
        </div>
        <div style="text-align:center;padding:10px 20px;background:#fff3e0;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#e65100;" id="dash-criticos">-</div>
          <div style="font-size:0.82em;color:#888;">Críticos &lt;30d</div>
        </div>
        <div style="text-align:center;padding:10px 20px;background:#fffde7;border-radius:8px;">
          <div style="font-size:1.8em;font-weight:700;color:#f57f17;" id="dash-proximos">-</div>
          <div style="font-size:0.82em;color:#888;">Próximos &lt;90d</div>
        </div>
      </div>
    </div>
  </div>

  <div id="stock" class="tab-content">
    <h2>&#128230; Stock por Lote</h2>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px;">
      <input type="text" id="stock-search" placeholder="MP, INCI, lote, proveedor..." oninput="filterStock()" style="width:210px;margin-top:0;">
      <div style="display:flex;gap:10px;"><button onclick="loadStock()">&#8635; Actualizar</button><button onclick="exportarExcelStock()" style="background:#217346;">&#128196; Descargar Excel</button></div>
      <span id="stock-count" style="color:#888;font-size:0.88em;"></span>
    </div>
    <div style="overflow-x:auto;">
    <table class="table" style="font-size:0.83em;">
      <thead><tr>
        <th>Cod. MP</th><th>Nombre INCI</th><th>Nombre Comercial</th>
        <th>Tipo</th><th>Proveedor</th>
        <th style="text-align:right;">Stock Min (g)</th><th>Lote</th>
        <th style="text-align:right;">Cantidad (g)</th>
        <th style="text-align:center;">Est.</th><th style="text-align:center;">Pos.</th>
        <th style="text-align:center;">Fecha Venc.</th>
        <th style="text-align:right;">Dias</th><th style="text-align:center;">Estado</th><th style="text-align:center;">Ajuste</th><th style="text-align:center;">Historial</th>
      </tr></thead>
      <tbody id="stock-body"><tr><td colspan="13" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
    </table>
    </div>
  
  <!-- MEE STOCK -->
  <div style="margin-top:32px;border-top:3px solid #2B7A78;padding-top:24px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
      <h2 style="margin:0;">&#128230; Stock Materiales de Envase & Empaque</h2>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <select id="mee-cat-filter" onchange="loadMEE()" style="width:auto;margin:0;padding:7px 12px;font-size:0.88em;">
          <option value="">Todas las categorias</option>
          <option>Envase</option><option>Tapa</option><option>Etiqueta</option>
          <option>Plegable</option><option>Serigrafia</option><option>Gotero</option>
          <option>Frasco</option><option>Contorno</option><option>Otro</option>
        </select>
        <input type="text" id="mee-search" placeholder="Buscar..." oninput="loadMEE()" style="width:160px;margin:0;padding:7px 12px;font-size:0.88em;">
        <button onclick="loadMEE()" style="padding:7px 14px;font-size:0.85em;">&#8635;</button>
        <button onclick="abrirNuevoMEE()" style="background:#27ae60;padding:7px 14px;font-size:0.85em;">+ Nuevo</button>
      </div>
    </div>
    <div id="nuevo-mee-form" style="display:none;background:#e8f5e9;border:2px solid #27ae60;border-radius:8px;padding:18px;margin-bottom:16px;">
      <h4 style="color:#1b5e20;margin-bottom:12px;">+ Nuevo Material E&E</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Codigo *</label><input type="text" id="nmee-cod" placeholder="ENV-XXX-01" style="text-transform:uppercase;"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Descripcion *</label><input type="text" id="nmee-desc" placeholder="Descripcion del material"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Categoria *</label>
          <select id="nmee-cat" style="width:100%;"><option>Envase</option><option>Tapa</option><option>Etiqueta</option><option>Plegable</option><option>Serigrafia</option><option>Gotero</option><option>Frasco</option><option>Contorno</option><option>Otro</option></select></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Proveedor</label><input type="text" id="nmee-prov" placeholder="Proveedor"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Stock Inicial (und)</label><input type="number" id="nmee-stock" value="2000"></div>
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Stock Minimo (und)</label><input type="number" id="nmee-min" value="1000"></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:12px;">
        <button onclick="crearMEE()" style="background:#1b5e20;">Crear</button>
        <button onclick="document.getElementById('nuevo-mee-form').style.display='none'" style="background:#95a5a6;">Cancelar</button>
      </div>
      <div id="nmee-msg" style="margin-top:8px;"></div>
    </div>
    <div style="overflow-x:auto;">
      <table class="table" style="font-size:0.84em;">
        <thead><tr>
          <th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Proveedor</th>
          <th style="text-align:right;">Stock Min</th>
          <th style="text-align:right;">Stock Actual</th>
          <th style="text-align:center;">Estado</th>
          <th style="text-align:center;">Ajuste</th>
          <th style="text-align:center;">Historial</th>
          <th style="text-align:center;">Compra</th>
        </tr></thead>
        <tbody id="mee-stock-body"><tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>
  </div>

  <div id="ingreso" class="tab-content">
    <div id="ing-panel-mp">
    <h2>&#128666; Ingreso de Materia Prima</h2>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
      <p style="color:#666;">Escribe el codigo MP y el sistema completa automaticamente desde el catalogo.</p>
      <button onclick="mostrarFormNuevaMP()" style="background:#27ae60;white-space:nowrap;margin-left:15px;">&#43; Nueva MP en Catalogo</button>
    </div>
    <div id="ing-nueva-mp" style="display:none;background:#e8f5e9;border:2px solid #27ae60;border-radius:8px;padding:18px;margin-bottom:15px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h4 style="color:#1b5e20;">&#43; Crear Nueva Materia Prima en el Catalogo</h4>
        <button onclick="ocultarFormNuevaMP()" style="background:#95a5a6;padding:4px 12px;font-size:0.85em;">&#10005; Cerrar</button>
      </div>
      <p style="font-size:0.88em;color:#2e7d32;margin-bottom:12px;">Esta MP quedara registrada en el catalogo y disponible para futuros ingresos.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group"><label>Codigo MP * (ej: MP00350)</label><input type="text" id="nmp-cod" placeholder="MP00350" style="text-transform:uppercase;"></div>
        <div class="form-group"><label>Nombre INCI *</label><input type="text" id="nmp-inci" placeholder="Ej: NIACINAMIDE"></div>
        <div class="form-group"><label>Nombre Comercial *</label><input type="text" id="nmp-nombre" placeholder="Ej: Niacinamida"></div>
        <div class="form-group"><label>Tipo</label><input type="text" id="nmp-tipo" placeholder="Ej: Activo, Emoliente, Conservante..."></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="nmp-prov" placeholder="Nombre del proveedor"></div>
        <div class="form-group"><label>Stock Minimo (g)</label><input type="number" id="nmp-smin" placeholder="0" value="500"></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:12px;">
        <button onclick="crearNuevaMP()" style="background:#1b5e20;">&#10003; Crear en Catalogo</button>
      </div>
      <div id="nmp-msg" style="margin-top:10px;"></div>
    </div>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:20px;">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        <div class="form-group"><label>Codigo MP *</label><div style="position:relative;"><input type="text" id="ing-cod" placeholder="Código (MP00001) o nombre..." autocomplete="off" style="text-transform:uppercase;" oninput="buscarMPIngreso(this.value)" onblur="setTimeout(ocultarDropMP,250)"><div id="mp-dropdown" style="position:absolute;top:100%;left:0;right:0;background:white;border:1px solid #2B7A78;border-radius:0 0 8px 8px;max-height:220px;overflow-y:auto;z-index:1000;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.15);"></div></div><datalist id="mp-sugerencias"></datalist><small id="ing-status" style="color:#667eea;font-size:0.85em;margin-top:4px;display:block;"></small></div>
        <div class="form-group"><label>Nombre INCI</label><input type="text" id="ing-inci" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Nombre Comercial</label><input type="text" id="ing-nombre" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Tipo</label><input type="text" id="ing-tipo" placeholder="Auto" readonly style="background:#f5f5f5;"></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="ing-prov" placeholder="Auto (editable)"></div>
      </div>
      <div id="ing-nueva-mp-inline" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:15px;margin-top:10px;">
        <h4 style="color:#856404;margin-bottom:10px;">&#43; Nueva Materia Prima — Datos para el Catalogo</h4><p style="font-size:0.88em;color:#666;margin-bottom:10px;">Al registrar el ingreso, esta MP quedara creada automaticamente en el catalogo.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="form-group"><label>Nombre INCI *</label><input type="text" id="ing-inci-new" placeholder="Ej: NIACINAMIDE"></div>
          <div class="form-group"><label>Tipo</label><input type="text" id="ing-tipo-new" placeholder="Ej: Activo, Emoliente..."></div>
          <div class="form-group"><label>Stock Minimo (g)</label><input type="number" id="ing-smin-new" placeholder="0" value="0"></div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
        <div class="form-group"><label>N Lote (vacio = auto)</label><input type="text" id="ing-lote" placeholder="Ej: LYPH250727"></div>
        <div class="form-group"><label>Cantidad recibida (g) *</label><input type="number" id="ing-cant" placeholder="0" step="0.01" oninput="calcularValorTotal()"></div>
        <div class="form-group"><label>Fecha Vencimiento</label><input type="date" id="ing-vence"></div>
        <div class="form-group"><label>Estanteria</label><input type="text" id="ing-est" placeholder="Ej: 9"></div>
        <div class="form-group"><label>Posicion</label><input type="text" id="ing-pos" placeholder="Ej: B"></div>
        <div class="form-group"><label>Precio por kg (COP)</label><input type="number" id="ing-precio-kg" placeholder="Ej: 45000" step="0.01" min="0" oninput="calcularValorTotal()"></div>
        <div class="form-group" style="grid-column:span 2;"><label>Valor total estimado (COP)</label><input type="text" id="ing-valor-total" placeholder="Se calcula al ingresar cantidad y precio" readonly style="background:#f0fff4;color:#27ae60;font-weight:600;border:1px solid #a8e6cf;"></div>
      </div>
      <!-- OC Receipt + Costos + Cuarentena -->
      <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:14px;margin:12px 0;">
        <div style="font-size:0.82em;font-weight:700;color:#e65100;margin-bottom:10px;">&#128230; VINCULAR A ORDEN DE COMPRA (opcional)</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
          <div class="form-group" style="margin:0;">
            <label>OC Pendiente</label>
            <select id="ing-oc-sel" onchange="autocompletarDesdeOC()" style="width:100%;">
              <option value="">-- Ingreso libre (sin OC) --</option>
            </select>
          </div>
          <div class="form-group" style="margin:0;">
            <label>N° Factura / Remision</label>
            <input type="text" id="ing-factura" placeholder="Ej: FAC-2026-1234">
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;padding:10px;background:#fff3e0;border-radius:6px;border:1px solid #ffe0b2;">
        <input type="checkbox" id="ing-cuarentena" style="width:18px;height:18px;">
        <label for="ing-cuarentena" style="margin:0;cursor:pointer;font-weight:600;color:#e65100;">
          &#128274; Ingresar en CUARENTENA (pendiente aprobacion de calidad)
        </label>
      </div>
      <div class="form-group" style="margin-top:10px;"><label>Observaciones</label><input type="text" id="ing-obs" placeholder="Opcional"></div>
      <div style="display:flex;gap:10px;margin-top:15px;flex-wrap:wrap;">
        <button onclick="registrarIngreso()" style="background:#27ae60;">&#10003; Registrar Entrada</button>
        <button onclick="generarRotuloIngreso()" style="background:#2980b9;" id="btn-rotulo-ing">&#128209; Generar Rotulo + Codigo de Barras</button>
        <button onclick="limpiarIngreso()" style="background:#95a5a6;">Limpiar</button>
      </div>
      <div id="ing-msg" style="margin-top:12px;"></div>
    </div>
    <h3 style="margin-bottom:10px;">Ultimas Entradas</h3>
    <div style="overflow-x:auto;"><table class="table" id="ing-hist">
      <thead><tr><th>Codigo</th><th>INCI</th><th>Nombre Comercial</th><th>Lote</th><th style="text-align:right;">g</th><th>Proveedor</th><th>Vence</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="8" style="text-align:center;color:#999;">Sin entradas</td></tr></tbody>
    </table></div>
    </div><!-- end ing-panel-mp -->
  </div>

  <div id="formulas" class="tab-content">
    <h2>&#129514; Formulas Maestras de Produccion</h2>
    <p style="color:#666;margin-bottom:18px;">Define la receta de cada producto. Al registrar una produccion, las MPs se descuentan automaticamente del inventario.</p>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:22px;">
      <h3 style="margin-bottom:12px;">Nueva Formula / Editar Existente</h3>
      <div style="display:grid;grid-template-columns:1fr 200px;gap:12px;">
        <div class="form-group"><label>Nombre del Producto</label><input type="text" id="formula-producto" placeholder="Ej: Renova C 10"></div>
        <div class="form-group"><label>Base (g) = 100%</label><input type="number" id="formula-base" value="1000"></div>
      </div>
      <div class="form-group"><label>Descripcion (opcional)</label><input type="text" id="formula-desc" placeholder="Descripcion breve"></div>
      <label style="display:block;margin-bottom:8px;font-weight:600;font-size:0.88em;color:#444;">Ingredientes (materias primas)</label>
      <div style="display:grid;grid-template-columns:140px 1fr 90px 38px;gap:6px;margin-bottom:6px;">
        <span style="font-size:0.8em;color:#888;font-weight:600;">CODIGO MP</span>
        <span style="font-size:0.8em;color:#888;font-weight:600;">NOMBRE MATERIAL</span>
        <span style="font-size:0.8em;color:#888;font-weight:600;">% EN FORMULA</span>
        <span></span>
      </div>
      <div id="fi-container"></div>
      <div style="display:flex;gap:10px;margin-top:10px;align-items:center;flex-wrap:wrap;">
        <button onclick="addFRow()" style="background:#28a745;">+ Ingrediente</button>
        <button onclick="guardarFormula()">&#128190; Guardar Formula</button>
        <span id="pct-total" style="font-size:0.9em;color:#666;font-weight:600;"></span>
      </div>
      <div id="formula-msg"></div>
    </div>
    <h3 style="margin-bottom:12px;">Formulas Guardadas</h3>
    <div id="formulas-list"><p style="color:#999;">Cargando...</p></div>
  </div>

  <div id="produccion" class="tab-content">
    <h2>&#127981; Registrar Produccion</h2>
    <p style="color:#666;margin-bottom:16px;">Si el producto tiene formula maestra, las MPs se descuentan automaticamente del inventario al registrar.</p>
    <div class="form-group">
      <label>Producto (con formula maestra)</label>
      <select id="prod-sel" onchange="previewProd()">
        <option value="">-- Selecciona un producto --</option>
      </select>
    </div>
    <div class="form-group">
      <label>O escribe nombre manualmente (sin formula)</label>
      <input type="text" id="prod-manual" placeholder="Producto sin formula registrada" oninput="previewProd()">
    </div>
    <div class="form-group">
      <label>Cantidad a producir (kg)</label>
      <input type="number" id="prod-kg" placeholder="Ej: 20" step="0.001" oninput="previewProd()">
    </div>
    <div id="prod-preview" style="background:#f0f8ff;border:1px solid #b8d4f0;border-radius:8px;padding:14px;margin-bottom:14px;display:none;">
      <strong style="color:#2c5f8a;">MPs que se descontaran automaticamente:</strong>
      <table class="table" style="margin-top:8px;">
        <thead><tr><th>Material</th><th style="text-align:right;">Cantidad (g)</th></tr></thead>
        <tbody id="prod-preview-body"></tbody>
      </table>
    </div>
    <div class="form-group">
      <label>Presentacion del producto</label>
      <input type="text" id="prod-presentacion" placeholder="Ej: 15ml, 30ml, 50g..." list="pres-sugerencias">
      <datalist id="pres-sugerencias">
        <option value="10ml"><option value="15ml"><option value="20ml"><option value="30ml">
        <option value="50ml"><option value="60ml"><option value="100ml"><option value="120ml">
        <option value="150ml"><option value="50g"><option value="100g"><option value="250g">
      </datalist>
    </div>
    <div class="form-group"><label>Observaciones</label><textarea id="prod-obs" rows="2" placeholder="Opcional"></textarea></div>
    <div style="background:#f0f9f0;border:1px solid #c3e6cb;border-radius:10px;padding:16px;margin-bottom:16px;">
      <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-weight:700;color:#1b5e20;margin-bottom:0;">
        <input type="checkbox" id="prod-pt-check" onchange="togglePTFields()" style="width:18px;height:18px;">
        &#127981; Registrar unidades en Stock PT (Producto Terminado)
      </label>
      <div id="prod-pt-fields" style="display:none;margin-top:14px;display:none;">
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
          <div class="form-group" style="margin:0;">
            <label>SKU Producto</label>
            <input type="text" id="prod-sku-pt" placeholder="Ej: TRX-15" list="sku-sugerencias">
            <datalist id="sku-sugerencias">
              <option value="LBHA-30"><option value="TRX-15"><option value="NIAC-30">
              <option value="AZHC-30"><option value="SBHA-30"><option value="ECEN-30">
              <option value="EILU-30"><option value="CUREA-50"><option value="GELH-120">
            </datalist>
          </div>
          <div class="form-group" style="margin:0;">
            <label>Unidades producidas</label>
            <input type="number" id="prod-uds-pt" placeholder="Ej: 500" min="1">
          </div>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <button onclick="simularProduccion()" style="background:#6c5ce7;">&#128269; Verificar Stock</button>
      <button onclick="iniciarRegistroProd()">&#9989; Registrar Produccion</button>
      <button onclick="abrirRotulos()" style="background:#c0392b;">&#128209; Generar Rotulos</button>
    </div>
    <div id="prod-simul-result" style="margin-top:12px;"></div>
    <div id="prod-msg"></div>
    <div id="mee-consumo-panel" style="display:none;margin-top:24px;background:#f0f9f0;border:2px solid #27ae60;border-radius:12px;padding:22px;">
      <h3 style="color:#1b5e20;margin-bottom:6px;">&#128230; Paso 2: Consumo de Materiales E&E</h3>
      <p style="font-size:0.88em;color:#555;margin-bottom:16px;">Completa el empaque usado en esta produccion. Marca <strong>No aplica</strong> si alguna categoria no corresponde.</p>
      <div id="mee-rows-container"></div>
      <div style="display:flex;gap:10px;margin-top:18px;">
        <button onclick="confirmarProdCompleta()" style="background:#1b5e20;font-size:1em;padding:11px 28px;">&#10003; Confirmar Produccion Completa</button>
        <button onclick="cancelarMEEConsumoProd()" style="background:#95a5a6;">Cancelar</button>
      </div>
      <div id="mee-consumo-msg" style="margin-top:10px;"></div>
    </div>
    <div style="margin-top:28px;border-top:2px solid #eee;padding-top:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><h3 style="color:#2B7A78;margin:0;">&#128202; Historial de Producciones</h3><button onclick="exportarExcelProducciones()" style="background:#217346;padding:7px 14px;font-size:0.85em;">&#128196; Descargar Excel</button></div>
      <table class="table"><thead><tr><th>Producto</th><th style="text-align:right;">Cantidad (kg)</th><th>Fecha</th><th>Operador</th><th style="text-align:center;">Estado</th></tr></thead>
      <tbody id="hist-prod-body"><tr><td colspan="6" style="text-align:center;color:#999;padding:16px;">Cargando...</td></tr></tbody></table>
    </div>
    <!-- TRAZABILIDAD INVIMA -->
    <div style="margin-top:28px;border-top:2px solid #eee;padding-top:20px;">
      <h3 style="color:#6c5ce7;margin:0 0 12px;">&#128203; Trazabilidad de Lotes (INVIMA)</h3>
      <p style="font-size:0.85em;color:#718096;margin:0 0 14px;">Dado un lote PT rastrea las MPs usadas y los clientes que lo recibieron. Dado un lote MP rastrea en qué producciones se consumio y a qué clientes llegó.</p>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
        <div style="flex:1;min-width:220px;">
          <label style="font-size:0.83em;font-weight:600;color:#555;">Lote PT (ej: PROD-00001)</label>
          <input id="trz-lote-pt" type="text" placeholder="PROD-00001" style="width:100%;padding:8px 12px;border:1px solid #ccc;border-radius:6px;margin-top:4px;">
        </div>
        <div style="flex:1;min-width:220px;">
          <label style="font-size:0.83em;font-weight:600;color:#555;">Lote MP (ej: ESP240115MP1)</label>
          <input id="trz-lote-mp" type="text" placeholder="ESP240115MP1" style="width:100%;padding:8px 12px;border:1px solid #ccc;border-radius:6px;margin-top:4px;">
        </div>
        <div style="display:flex;align-items:flex-end;gap:8px;">
          <button onclick="buscarTrazabilidadPT()" style="background:#6c5ce7;padding:8px 16px;">&#128269; Buscar PT&#8594;MP</button>
          <button onclick="buscarTrazabilidadMP()" style="background:#00b894;padding:8px 16px;">&#128269; Buscar MP&#8594;PT</button>
        </div>
      </div>
      <div id="trz-result" style="margin-top:10px;"></div>
    </div>
  </div>

  <div id="abc" class="tab-content">
    <h2>&#128200; Analisis ABC de Inventario</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:16px 20px;margin-bottom:18px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Para que sirve este modulo:</strong> Clasifica todas las materias primas segun el valor de stock que representan (Pareto 80/20).
      <ul style="margin:8px 0 0 16px;padding:0;">
        <li><span style="background:#28a745;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">A</span> — Top 80% del stock total. Son las MPs mas criticas: maxima atencion en control y reorden.</li>
        <li><span style="background:#fd7e14;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">B</span> — 80-95% acumulado. Control intermedio.</li>
        <li><span style="background:#6c757d;color:white;padding:1px 8px;border-radius:8px;font-weight:700;font-size:0.85em;">C</span> — 95-100%. Son muchos items pero representan poco stock. Control basico.</li>
      </ul>
      <p style="margin:8px 0 0;"><strong>Uso practico:</strong> Las MPs clase A son las que nunca pueden quedarse sin stock. Usar para definir frecuencia de conteo fisico y prioridad de compra.</p>
    </div>
    <button onclick="loadABC()" style="padding:9px 22px;background:#667eea;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;">&#128257; Actualizar Analisis</button>
    <div id="abc-results" style="margin-top:18px;"></div>
  </div>

  <div id="alertas" class="tab-content">
    <h2>&#9888; Alertas de Inventario</h2>
    <div style="background:#fff3e0;border:2px solid #ff9800;border-radius:10px;padding:18px;margin-bottom:20px;">
      <h3 style="color:#e65100;margin-bottom:10px;">&#128197; Lotes que vencen en 30 dias o menos</h3>
      <div id="venc30-content" style="color:#999;">Cargando...</div>
    </div>

    <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:16px;margin-bottom:20px;">
      <h3 style="color:#856404;margin-bottom:10px;">&#128308; MPs bajo stock minimo (basado en plan anual)</h3>
      <p style="font-size:0.88em;color:#664d03;margin-bottom:12px;">Stock minimo calculado: consumo anual / 12 x 2 meses x 1.10 de buffer</p>
      <div id="alertas-reabas-tabla">
        <table class="table">
          <thead><tr><th>Tipo</th><th>Código</th><th>Material</th><th>Proveedor</th><th style="text-align:right;">Mínimo</th><th style="text-align:right;">Actual</th><th style="text-align:right;">Déficit</th><th style="text-align:center;">Criticidad</th><th style="text-align:center;">Acción</th></tr></thead>
          <tbody id="reabas-body"><tr><td colspan="9" style="text-align:center;color:#999;">Calculando...</td></tr></tbody>
        </table>
      </div>
    </div>

    <h3 style="margin-bottom:10px;">Alertas manuales de stock</h3>
    <button onclick="loadAlertas()" style="margin-bottom:12px;">Actualizar</button>
    <table class="table" id="alertas-table">
      <thead><tr><th>Material</th><th>Stock Actual</th><th>Stock Minimo</th><th>Estado</th><th>Fecha</th></tr></thead>
      <tbody><tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr></tbody>
    </table>

    <!-- ALERTAS MEE -->
    <div style="margin-top:28px;border-top:3px solid #2B7A78;padding-top:24px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
        <h3 style="color:#c0392b;margin:0;">&#128308; Materiales E&E bajo stock minimo</h3>
        <div style="display:flex;gap:8px;">
          <button onclick="loadAlertasMEE()" style="padding:7px 14px;font-size:0.85em;">&#8635; Actualizar</button>
          <button onclick="generarOCsDesdeAlertasMEE()" style="background:#4A6741;padding:7px 16px;font-size:0.85em;">&#9889; Generar OCs automaticas MEE</button>
        </div>
      </div>
      <div style="overflow-x:auto;">
        <table class="table" style="font-size:0.85em;">
          <thead><tr>
            <th>Codigo</th><th>Descripcion</th><th>Categoria</th>
            <th style="text-align:right;">Min (und)</th>
            <th style="text-align:right;">Stock Actual (und)</th>
            <th style="text-align:right;">Deficit</th>
            <th style="text-align:center;">Nivel</th>
            <th style="text-align:center;">Accion</th>
          </tr></thead>
          <tbody id="mee-alertas-body"><tr><td colspan="8" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  </div>

  <div id="movimientos" class="tab-content">
    <h2>&#128203; Movimientos de Inventario</h2>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:18px;">
      <h3 style="margin-bottom:12px;">Registrar Movimiento Manual</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
        <div class="form-group"><label>Codigo MP</label><input type="text" id="mov-id" placeholder="MP00001"></div>
        <div class="form-group"><label>Nombre Material</label><input type="text" id="mov-nombre" placeholder="Nombre"></div>
        <div class="form-group"><label>Cantidad (g)</label><input type="number" id="mov-cant" placeholder="0" step="0.01"></div>
        <div class="form-group"><label>Tipo</label>
          <select id="mov-tipo"><option value="Entrada">Entrada</option><option value="Salida">Salida</option></select>
        </div>
      </div>
      <div class="form-group"><label>Observaciones</label><input type="text" id="mov-obs" placeholder="Opcional"></div>
      <button onclick="registrarMov()">Registrar</button>
      <div id="mov-msg"></div>
    </div>
    <div style="display:flex;gap:10px;margin-bottom:10px;"><button onclick="loadMovimientos()">Ver Ultimos Movimientos</button><button onclick="exportarExcelMovimientos()" style="background:#217346;">&#128196; Descargar Excel</button></div>
    <table class="table" id="mov-table">
      <thead><tr><th>Material</th><th>Cantidad (g)</th><th>Tipo</th><th>Fecha</th><th>Observaciones</th><th>Anular</th></tr></thead>
      <tbody><tr><td colspan="6" style="text-align:center;color:#999;">Sin movimientos</td></tr></tbody>
    </table>
  </div>

  <div id="cuarentena" class="tab-content">
    <h2>&#128274; Control de Calidad — Recepcion de Materiales</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Como funciona:</strong> Cuando recibes una MP en la pestana <strong>Ingreso MP</strong> y marcas el checkbox <strong>"Poner en cuarentena"</strong>, ese lote aparece aqui hasta que alguien con rol admin lo revise y apruebe o rechace conforme a COC-PRO-001. Mientras esta en cuarentena, el sistema NO permite usarlo en produccion.<br>
      <span style="color:#27ae60;font-weight:600;">&#10003; Si esta vacia: ningun lote esta pendiente de revision CC — es la situacion ideal.</span> Si recibes un lote con dudas de calidad, usa "Poner en cuarentena" al hacer el ingreso.
    </div>
    <div id="cuar-msg"></div>

    <!-- Tabla de lotes pendientes -->
    <table class="table" id="cuar-table">
      <thead><tr><th>Codigo</th><th>INCI</th><th>Nombre</th><th>Lote</th><th>Cant. (g)</th><th>Proveedor</th><th>OC</th><th>Fecha ingreso</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="cuar-tbody"><tr><td colspan="10" style="text-align:center;color:#999;">Sin lotes en cuarentena</td></tr></tbody>
    </table>

    <!-- Modal de revision CC -->
    <div id="cc-modal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center;">
      <div style="background:#fff;border-radius:14px;padding:32px;max-width:680px;width:95%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
          <h3 style="color:#1C2B30;margin:0;">&#128203; Revision CC — <span id="cc-modal-lote"></span></h3>
          <button onclick="cerrarCCModal()" style="background:none;border:none;font-size:1.4em;cursor:pointer;color:#999;">&#x2715;</button>
        </div>
        <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:0.88em;">
          <strong>COC-PRO-001 v03</strong> — Todos los campos son obligatorios. La firma queda registrada con timestamp en el sistema y no puede modificarse.
        </div>

        <!-- Info del lote -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;background:#f8f9ff;border-radius:8px;padding:14px;margin-bottom:20px;font-size:0.88em;" id="cc-lote-info"></div>

        <!-- Checklist COC-PRO-001 -->
        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:14px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">6. Revision Documental</h4>
          <div style="display:flex;flex-direction:column;gap:10px;">
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-coa-ok" style="width:18px;height:18px;">
              <span>COA del proveedor presente y correspondiente al lote recibido</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-lote-coincide" style="width:18px;height:18px;">
              <span>Numero de lote del COA coincide exactamente con el lote del empaque</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-coa-vigente" style="width:18px;height:18px;">
              <span>COA vigente — no vencido segun politica de re-analisis</span>
            </label>
            <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
              <input type="checkbox" id="cc-ficha-ok" style="width:18px;height:18px;">
              <span>Ficha tecnica del proveedor disponible en archivo CC</span>
            </label>
          </div>
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:14px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">9. Prueba de Solubilidad / Compatibilidad</h4>
          <div style="display:flex;gap:12px;">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-solub" value="ACEPTACION" id="cc-solub-ok"> <span style="color:#27ae60;">ACEPTACION</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-solub" value="RECHAZO" id="cc-solub-fail"> <span style="color:#e74c3c;">RECHAZO</span>
            </label>
          </div>
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:10px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">Resultado AQL / Inspeccion organolectica</h4>
          <div style="display:flex;gap:12px;margin-bottom:12px;">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="CONFORME" id="cc-aql-ok"> <span style="color:#27ae60;">CONFORME</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="NO_CONFORME" id="cc-aql-fail"> <span style="color:#e74c3c;">NO CONFORME</span>
            </label>
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;padding:10px 18px;border:2px solid #dde;border-radius:8px;font-size:0.9em;font-weight:600;">
              <input type="radio" name="cc-aql" value="CUARENTENA_EXTENDIDA" id="cc-aql-ext"> <span style="color:#e67e22;">CUARENTENA EXTENDIDA</span>
            </label>
          </div>
          <input type="text" id="cc-aql-obs" placeholder="Observaciones AQL (requerido si NO CONFORME o CUARENTENA EXTENDIDA)" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:0.88em;">
        </div>

        <div style="margin-bottom:20px;">
          <h4 style="color:#2c3e50;margin-bottom:10px;font-size:0.95em;text-transform:uppercase;letter-spacing:1px;">Muestra de retencion tomada</h4>
          <label style="display:flex;align-items:center;gap:10px;cursor:pointer;font-size:0.9em;">
            <input type="checkbox" id="cc-muestra-ret" style="width:18px;height:18px;">
            <span>Se tomo muestra de retencion y quedo identificada en laboratorio CC</span>
          </label>
        </div>

        <div style="margin-bottom:24px;">
          <label style="display:block;font-weight:600;margin-bottom:6px;font-size:0.9em;color:#555;">Observaciones adicionales</label>
          <textarea id="cc-obs-final" rows="3" placeholder="Condiciones especiales, hallazgos, acciones tomadas..." style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:0.88em;resize:vertical;"></textarea>
        </div>

        <!-- Decision final -->
        <div style="background:#f8f9ff;border-radius:8px;padding:14px;margin-bottom:20px;">
          <p style="font-size:0.88em;color:#555;margin-bottom:10px;"><strong>Decision final:</strong> Se determina automaticamente por el resultado AQL y solubilidad. Firmante: <strong id="cc-firmante"></strong></p>
          <div style="display:flex;gap:10px;justify-content:flex-end;">
            <button onclick="cerrarCCModal()" style="padding:10px 20px;background:#f0f0f0;color:#555;border:none;border-radius:8px;font-weight:600;cursor:pointer;">Cancelar</button>
            <button onclick="enviarRevisionCC()" id="cc-submit-btn" style="padding:10px 28px;background:#2B7A78;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:0.95em;">Firmar y Registrar</button>
          </div>
        </div>
        <div id="cc-modal-msg"></div>
      </div>
    </div>
  </div>

  <div id="trazabilidad" class="tab-content">
    <h2>&#128269; Trazabilidad de Lotes</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Herramienta de busqueda — no es un dashboard.</strong> Escribe el numero de lote de una MP (el codigo que aparece en la etiqueta de recepcion, ej: <code style="background:#d0eaf9;padding:1px 5px;border-radius:4px;">ESP260417ACE</code>) y el sistema muestra: quien recibio ese lote, de que proveedor, en que fecha, y en que producciones fue utilizado. Util para auditorias, reclamos de proveedor y trazabilidad BPM.
    </div>
    <div id="trz-msg"></div>
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:18px;display:flex;gap:12px;align-items:flex-end;">
      <div style="flex:1;">
        <label style="display:block;font-weight:600;margin-bottom:4px;color:#555;">Numero de Lote</label>
        <input type="text" id="trz-lote" placeholder="Ej: ESP260417ACE" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;font-size:1em;">
      </div>
      <button onclick="buscarTrazabilidad()" style="padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;">Buscar</button>
    </div>
    <div id="trz-result-lote" style="display:none;">
      <div style="background:#fff;border:1px solid #dde;border-radius:10px;padding:20px;margin-bottom:16px;">
        <h3 style="color:#2c3e50;margin:0 0 12px;">Ingreso del Lote</h3>
        <div id="trz-ingreso"></div>
      </div>
      <div style="background:#fff;border:1px solid #dde;border-radius:10px;padding:20px;">
        <h3 style="color:#2c3e50;margin:0 0 12px;">Uso en Produccion (<span id="trz-nprod">0</span> registros)</h3>
        <table class="table"><thead><tr><th>Producto</th><th>Fecha</th><th>Operador</th><th>Cantidad usada (g)</th></tr></thead>
        <tbody id="trz-prod-tbody"></tbody></table>
      </div>
    </div>
  </div>


  <div id="conteo" class="tab-content">
    <h2>&#9989; Conteo Fisico Ciclico — BDG-FOR-003</h2>
    <div style="background:#e8f4fd;border:1px solid #bee5f8;border-radius:10px;padding:14px 20px;margin-bottom:16px;font-size:0.9em;color:#1a4a6b;">
      <strong>&#8505; Para que sirve:</strong> Permite verificar fisicamente el stock de una estanteria contra lo que dice el sistema. El operario cuenta los gramos reales, los ingresa, y el sistema calcula diferencias. Si la diferencia es mayor al 5% del valor, requiere aprobacion de gerencia antes de ajustar. Queda registro firmado conforme a BDG-PRO-002.<br>
      <strong>Como usar:</strong> (1) El dropdown se llena automaticamente con las estanterias que tienen stock. Si aparece <em>"Sin estanteria"</em>, son MPs ingresadas sin asignar ubicacion fisica — igual puedes contarlas. (2) Selecciona estanteria + escribe tu nombre + clic <strong>Iniciar Conteo</strong>. (3) Ingresa el peso fisico de cada MP. (4) Guarda y cierra.
    </div>

    <!-- Programacion automatica semanal -->
    <div id="cnt-prog-card" style="background:linear-gradient(135deg,#f0faf9 0%,#e8f8f5 100%);border:2px solid #2B7A78;border-radius:12px;padding:18px 20px;margin-bottom:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <h3 style="margin:0;color:#2B7A78;font-size:1em;">&#128197; Programacion Ciclica Automatica</h3>
        <span style="font-size:0.8em;color:#666;">Rota por todas las estanterias — cada lunes una nueva</span>
      </div>
      <div id="cnt-prog-tabla" style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
          <thead><tr style="background:#2B7A78;color:#fff;"><th style="padding:7px 12px;text-align:left;">Semana</th><th style="padding:7px 12px;text-align:left;">Lunes</th><th style="padding:7px 12px;text-align:left;">Estanteria asignada</th><th style="padding:7px 12px;text-align:center;">Estado</th><th style="padding:7px 12px;text-align:center;">Accion</th></tr></thead>
          <tbody id="cnt-prog-rows"><tr><td colspan="5" style="text-align:center;padding:14px;color:#999;">Cargando...</td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- Selector de estanteria manual -->
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:20px;display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:end;">
      <div>
        <label style="display:block;font-weight:600;margin-bottom:4px;font-size:0.88em;color:#555;">Estanteria / Seccion a contar</label>
        <select id="cnt-est-sel" style="width:100%;padding:10px;border:1px solid #dde;border-radius:8px;">
          <option value="">-- Selecciona estanteria --</option>
        </select>
      </div>
      <div>
        <label style="display:block;font-weight:600;margin-bottom:4px;font-size:0.88em;color:#555;">Responsable</label>
        <input type="text" id="cnt-responsable" placeholder="Nombre operario" style="padding:10px;border:1px solid #dde;border-radius:8px;">
      </div>
      <button onclick="iniciarConteo()" style="padding:10px 22px;background:#2B7A78;color:#fff;border:none;border-radius:8px;font-weight:700;cursor:pointer;">Iniciar Conteo</button>
    </div>

    <!-- Panel de conteo activo -->
    <div id="cnt-panel" style="display:none;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div>
          <span id="cnt-numero" style="font-family:monospace;font-weight:700;font-size:1.1em;color:#2B7A78;"></span>
          <span style="margin-left:12px;font-size:0.85em;color:#888;">Estanteria: <strong id="cnt-est-label"></strong></span>
        </div>
        <div style="display:flex;gap:10px;">
          <button onclick="guardarConteo()" style="padding:8px 18px;background:#27ae60;color:#fff;border:none;border-radius:7px;font-weight:600;cursor:pointer;">Guardar</button>
          <button onclick="cerrarConteo()" style="padding:8px 18px;background:#e67e22;color:#fff;border:none;border-radius:7px;font-weight:600;cursor:pointer;">Cerrar Conteo</button>
        </div>
      </div>

      <div id="cnt-resumen" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:14px;font-size:0.88em;"></div>

      <table class="table" id="cnt-tabla">
        <thead>
          <tr>
            <th>Codigo</th><th>INCI</th><th>Material</th>
            <th style="text-align:right;">Stock Sistema (g)</th>
            <th style="text-align:right;width:130px;">Stock Fisico (g)</th>
            <th style="text-align:right;">Diferencia</th>
            <th>%</th><th>Valor diff</th>
            <th style="width:160px;">Causa</th>
            <th>Ajuste</th>
          </tr>
        </thead>
        <tbody id="cnt-tbody"></tbody>
      </table>
    </div>

    <!-- Historial de conteos -->
    <div style="margin-top:28px;">
      <h3 style="color:#2c3e50;margin-bottom:12px;">Historial de Conteos</h3>
      <div id="cnt-msg"></div>
      <table class="table">
        <thead><tr><th>Numero</th><th>Estanteria</th><th>Fecha</th><th>Responsable</th><th>Estado</th><th>Total MPs</th><th>Con diferencia</th><th>Pend. Gerencia</th></tr></thead>
        <tbody id="cnt-hist-tbody"><tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos registrados</td></tr></tbody>
      </table>
    </div>
  </div>


  <!-- ==================== TAB: EMPAQUE MEE ==================== -->
  <div id="empaque" class="tab-content">
    <h2>&#128230; Material de Empaque y Envase (MEE)</h2>
    <p style="color:#666;font-size:0.9em;margin-bottom:16px;">Control de stock, recepciones, consumos y trazabilidad de material de empaque por batch de produccion.</p>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px;">
      <div style="background:#2B7A78;color:white;padding:16px;border-radius:10px;text-align:center;"><div style="font-size:1.5em;">&#128230;</div><div style="font-size:2em;font-weight:700;" id="mee-c-total">0</div><div style="font-size:0.82em;opacity:0.9;">Total MEE Activos</div></div>
      <div id="mee-card-bajo" style="background:#e74c3c;color:white;padding:16px;border-radius:10px;text-align:center;"><div style="font-size:1.5em;">&#9888;</div><div style="font-size:2em;font-weight:700;" id="mee-c-bajo">0</div><div style="font-size:0.82em;opacity:0.9;">Bajo Minimo</div></div>
      <div style="background:#3498db;color:white;padding:16px;border-radius:10px;text-align:center;"><div style="font-size:1.5em;">&#128202;</div><div style="font-size:2em;font-weight:700;" id="mee-c-semana">0</div><div style="font-size:0.82em;opacity:0.9;">Mov. Esta Semana</div></div>
      <div style="background:#9b59b6;color:white;padding:16px;border-radius:10px;text-align:center;"><div style="font-size:1.5em;">&#128229;</div><div style="font-size:2em;font-weight:700;" id="mee-c-mes">0</div><div style="font-size:0.82em;opacity:0.9;">Entradas Este Mes</div></div>
    </div>
    <div id="mee-alertas-panel" style="margin-bottom:18px;"></div>
    <div style="display:grid;grid-template-columns:1fr 370px;gap:18px;margin-bottom:22px;">
      <div>
        <div style="display:flex;gap:10px;margin-bottom:10px;align-items:center;">
          <select id="mee-cat-filter-bodega" style="flex:1;width:auto;" onchange="cargarMeeStock()"><option value="">Todas las categorias</option></select>
          <button onclick="cargarMeeStock()" style="white-space:nowrap;">&#8635; Actualizar</button>
        </div>
        <div style="overflow-x:auto;">
          <table class="table"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Stock</th><th>Minimo</th><th>Estado</th><th>Ultimo Mov.</th><th>Rotacion</th></tr></thead>
          <tbody id="mee-stock-tbody"><tr><td colspan="8" style="text-align:center;color:#999;">Cargando...</td></tr></tbody></table>
        </div>
      </div>
      <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;">
        <h3 style="margin-bottom:14px;color:#2B7A78;font-size:1em;">&#9998; Registrar Movimiento</h3>
        <div class="form-group"><label>Tipo</label>
          <select id="mee-tipo" onchange="meeActualizarTipo(this.value)">
            <option value="Entrada">&#128229; Entrada - recepcion</option>
            <option value="Salida">&#128228; Salida - consumo en produccion</option>
            <option value="Ajuste">&#9878; Ajuste de inventario</option>
          </select></div>
        <div class="form-group"><label>Material MEE</label>
          <select id="mee-codigo-sel" onchange="meeSelChange()"><option value="">-- Seleccionar material --</option></select></div>
        <div id="mee-stock-preview" style="display:none;background:#e8f4fd;border-radius:6px;padding:7px 12px;margin-bottom:10px;font-size:0.88em;color:#1a4a6b;"></div>
        <div class="form-group"><label>Cantidad</label><input type="number" id="mee-cantidad" min="1" step="1" placeholder="0"></div>
        <div class="form-group"><label>Unidad</label><input type="text" id="mee-unidad" value="und" placeholder="und / cajas / frascos"></div>
        <div id="mee-lote-group" class="form-group"><label>Lote / Ref. proveedor</label><input type="text" id="mee-lote" placeholder="Ej: LOT-2026-001"></div>
        <div id="mee-batch-group" class="form-group" style="display:none;"><label>Batch de produccion</label><input type="text" id="mee-batch" placeholder="Ej: BATCH-2026-001"></div>
        <div class="form-group"><label>Observaciones</label><textarea id="mee-obs" rows="2" placeholder="Opcional..."></textarea></div>
        <button style="width:100%;" onclick="registrarMeeMovimiento()">&#10003; Registrar</button>
        <div id="mee-form-msg" style="margin-top:8px;"></div>
      </div>
    </div>
    <div style="margin-bottom:22px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <h3 style="color:#444;">Historial de Movimientos</h3>
        <button onclick="cargarMeeHistorial()" style="background:#555;">Ver todos</button>
      </div>
      <div style="overflow-x:auto;">
        <table class="table"><thead><tr><th>#</th><th>Codigo</th><th>Descripcion</th><th>Tipo</th><th>Cantidad</th><th>Lote/Batch</th><th>Responsable</th><th>Fecha</th><th></th></tr></thead>
        <tbody id="mee-hist-tbody"><tr><td colspan="9" style="text-align:center;color:#999;">Sin movimientos</td></tr></tbody></table>
      </div>
    </div>
    <div style="background:#f0f8f0;border:1px solid #c3e6cb;border-radius:10px;padding:20px;">
      <h3 style="margin-bottom:12px;color:#155724;">&#128269; Trazabilidad MEE</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
        <div>
          <label style="font-weight:600;font-size:0.88em;color:#155724;">Por Batch de Produccion</label>
          <div style="display:flex;gap:8px;margin-top:5px;"><input type="text" id="mee-traz-batch" placeholder="Ej: BATCH-2026-001" style="flex:1;"><button onclick="buscarTrazabilidadBatch()" style="white-space:nowrap;background:#155724;">Buscar</button></div>
        </div>
        <div>
          <label style="font-weight:600;font-size:0.88em;color:#155724;">Por Codigo MEE</label>
          <div style="display:flex;gap:8px;margin-top:5px;"><input type="text" id="mee-traz-codigo" placeholder="Ej: MEE-CAJ-001" style="flex:1;"><button onclick="buscarTrazabilidadMee()" style="white-space:nowrap;background:#155724;">Buscar</button></div>
        </div>
      </div>
      <div id="mee-traz-result"></div>
    </div>
  </div>
  <!-- ==================== /TAB EMPAQUE MEE ==================== -->

  </div>

</div>

<div id="acondicionamiento" class="tab-content">
<div style="padding:18px">
<h2 style="margin:0 0 14px;color:#1a4a7a">&#128230; Acondicionamiento PT</h2>
<div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">
<h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Batch de Acondicionamiento</h3>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
<div><label style="font-size:12px;color:#555">Lote PT</label><input id="ac-lote" placeholder="LT-2026-001" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Producto</label><input id="ac-prod" placeholder="LBHA 30ml" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Presentación</label><input id="ac-pres" placeholder="Frasco 30ml" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Batch (g)</label><input id="ac-batch" type="number" placeholder="2000" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Unidades Producidas</label><input id="ac-uds" type="number" placeholder="66" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Fecha</label><input id="ac-fecha" type="date" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
</div>
<div style="margin-top:10px"><label style="font-size:12px;color:#555">Observaciones</label><textarea id="ac-obs" rows="2" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></textarea></div>
<button onclick="registrarAcond()" style="margin-top:10px;background:#1a4a7a;color:#fff;padding:9px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold">+ Registrar Batch</button>
</div>
<div id="ac-table-wrap">
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#1a4a7a;color:#fff"><th style="padding:8px">Lote</th><th style="padding:8px">Producto</th><th style="padding:8px">Presentación</th><th style="padding:8px">Batch(g)</th><th style="padding:8px">Uds</th><th style="padding:8px">Fecha</th><th style="padding:8px">Operador</th><th style="padding:8px">Estado</th><th style="padding:8px">Acción</th></tr></thead>
<tbody id="ac-tbody"></tbody>
</table></div>
</div></div>

<div id="liberacion" class="tab-content">
<div style="padding:18px">
<h2 style="margin:0 0 14px;color:#1a4a7a">&#9989; Liberación & Entrega</h2>
<div style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">
<h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Lote para Liberación</h3>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
<div><label style="font-size:12px;color:#555">Lote PT</label><input id="lb-lote" placeholder="LT-2026-001" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Producto</label><input id="lb-prod" placeholder="LBHA 30ml" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Presentación</label><input id="lb-pres" placeholder="Frasco 30ml" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Unidades</label><input id="lb-uds" type="number" placeholder="66" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Fecha Producción</label><input id="lb-fprod" type="date" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Destino</label><select id="lb-dest" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px"><option value="ANIMUS">ANÍMUS Lab</option><option value="MAQUILA">Maquila</option><option value="OTRO">Otro</option></select></div>
</div>
<div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:10px">
<div><label style="font-size:12px;color:#555">Cliente</label><input id="lb-cli" placeholder="Nombre cliente" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
<div><label style="font-size:12px;color:#555">Observaciones</label><input id="lb-obs" placeholder="Observaciones CC" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box"></div>
</div>
<button onclick="registrarLiberacion()" style="margin-top:10px;background:#1a4a7a;color:#fff;padding:9px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold">+ Enviar a Control de Calidad</button>
</div>
<div style="margin-bottom:10px">
<button onclick="loadLiberaciones('')" style="background:#6c757d;color:#fff;padding:5px 12px;border:none;border-radius:4px;margin-right:5px;cursor:pointer">Todas</button>
<button onclick="loadLiberaciones('Pendiente CC')" style="background:#fd7e14;color:#fff;padding:5px 12px;border:none;border-radius:4px;margin-right:5px;cursor:pointer">Pendiente CC</button>
<button onclick="loadLiberaciones('Liberado')" style="background:#28a745;color:#fff;padding:5px 12px;border:none;border-radius:4px;margin-right:5px;cursor:pointer">Liberadas</button>
<button onclick="loadLiberaciones('Rechazado')" style="background:#dc3545;color:#fff;padding:5px 12px;border:none;border-radius:4px;cursor:pointer">Rechazadas</button>
</div>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<thead><tr style="background:#1a4a7a;color:#fff"><th style="padding:8px">Lote</th><th style="padding:8px">Producto</th><th style="padding:8px">Uds</th><th style="padding:8px">Destino</th><th style="padding:8px">Cliente</th><th style="padding:8px">F.Prod</th><th style="padding:8px">F.Lib</th><th style="padding:8px">Aprobado por</th><th style="padding:8px">Estado</th><th style="padding:8px">Acción</th></tr></thead>
<tbody id="lb-tbody"></tbody>
</table>
</div></div>
<script>
var fData=[], allStock=[], _cat={}, _ultimoIng=null;
var _lotes=[], _lotesFull=[], _meeData=[], _prodPendiente=null;
var OPER_ACTUAL='{usuario}';
document.addEventListener('DOMContentLoaded',function(){
  // Restaurar operador desde localStorage si no vino por sesión
  if(!OPER_ACTUAL){
    try{var saved=localStorage.getItem('espagiria_operador');if(saved)OPER_ACTUAL=saved;}catch(e){}
  }
  var c=document.getElementById('oper-chip');
  if(OPER_ACTUAL){
    if(c) c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+OPER_ACTUAL+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
    loadDashboardCompleto();loadFormulas();
  } else {
    // Sin operador identificado: mostrar modal antes de cargar
    document.getElementById('modal-operador').style.display='flex';
    setTimeout(function(){var inp=document.getElementById('oper-input');if(inp)inp.focus();},150);
  }
});
var _ajDat={};
function _eq(s){return (s||'').split("'").join('&#39;');}
function selOper(n){
  OPER_ACTUAL=n;
  try{localStorage.setItem('espagiria_operador',n);}catch(e){}
  document.getElementById('modal-operador').style.display='none';
  var c=document.getElementById('oper-chip');if(c)c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+n+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
  loadDashboardCompleto();loadFormulas();
}
function cambiarOperador(){
  try{localStorage.removeItem('espagiria_operador');}catch(e){}
  document.getElementById('oper-input').value=OPER_ACTUAL||'';
  document.getElementById('modal-operador').style.display='flex';
  setTimeout(function(){document.getElementById('oper-input').focus();},100);
}
function confirmarOper(){var inp=document.getElementById('oper-input');var n=(inp?inp.value:'').trim();if(!n){var e=document.getElementById('oper-error');if(e)e.style.display='block';return;}selOper(n);}
function abrirAjusteIdx(idx){
  var i=_lotes[idx];
  if(!i)return;
  abrirAjuste(i.material_id,i.material_nombre,i.lote||"",i.cantidad_g);
}
async function abrirAjuste(mid,mn,lt,sa){
  if(!OPER_ACTUAL){alert('Primero selecciona tu nombre al inicio');return;}
  _ajDat={mid:mid,mn:mn,lt:lt,sa:sa};
  document.getElementById('ajuste-info').textContent=mid+' — '+mn+(lt&&lt!='S/L'?' (Lote: '+lt+')':'');
  document.getElementById('ajuste-sistema').value=sa;
  document.getElementById('ajuste-fisico').value='';
  document.getElementById('ajuste-obs').value='';
  document.getElementById('ajuste-msg').innerHTML='';
  document.getElementById('ajuste-smin-msg').innerHTML='';
  document.getElementById('ajuste-consumo-msg').innerHTML='';
  document.getElementById('ajuste-arch-msg').innerHTML='';
  document.getElementById('ajuste-consumo').value='';
  try{var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid));if(r.ok){var d=await r.json();document.getElementById('ajuste-smin').value=d.stock_minimo||0;}}catch(e){document.getElementById('ajuste-smin').value=0;}
  document.getElementById('modal-ajuste').style.display='flex';
}
async function actualizarStockMinimo(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  var val=parseFloat(document.getElementById('ajuste-smin').value);
  if(isNaN(val)||val<0){document.getElementById('ajuste-smin-msg').innerHTML='<span style="color:red;">Valor inválido</span>';return;}
  var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid)+'/stock-minimo',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({stock_minimo:val})});
  var d=await r.json();
  document.getElementById('ajuste-smin-msg').innerHTML=r.ok?'<span style="color:#28a745;">✓ Actualizado</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  if(r.ok) setTimeout(loadAlertasReabas,500);
}
async function registrarConsumo(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  var cant=parseFloat(document.getElementById('ajuste-consumo').value);
  if(isNaN(cant)||cant<=0){document.getElementById('ajuste-consumo-msg').innerHTML='<span style="color:red;">Cantidad positiva requerida</span>';return;}
  var r=await fetch('/api/consumo-manual',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo_mp:mid,cantidad:cant,lote:_ajDat.lt||'',operador:OPER_ACTUAL})});
  var d=await r.json();
  document.getElementById('ajuste-consumo-msg').innerHTML=r.ok?'<span style="color:#28a745;">✓ '+d.message+'</span>':'<span style="color:red;">'+(d.error||'Error')+'</span>';
  if(r.ok){var ns=Math.max(0,(_ajDat.sa||0)-cant);document.getElementById('ajuste-sistema').value=ns;_ajDat.sa=ns;document.getElementById('ajuste-consumo').value='';setTimeout(loadStock,500);}
}
async function archivarMP(){
  var mid=_ajDat&&_ajDat.mid;if(!mid)return;
  if(!confirm('Archivar '+mid+' — '+(_ajDat.mn||'')+'. Quedará oculto del catálogo activo. ¿Confirmar?'))return;
  try{
    var r=await fetch('/api/maestro-mps/'+encodeURIComponent(mid)+'/archivar',{method:'PUT',headers:{'Content-Type':'application/json'}});
    var d={}; try{d=await r.json();}catch(je){}
    document.getElementById('ajuste-arch-msg').innerHTML=r.ok?'<span style="color:#28a745;">✓ Archivado</span>':'<span style="color:red;">'+(d.error||'Error al archivar')+'</span>';
    setTimeout(function(){cerrarAjuste();loadStock();},1500);
  }catch(e){
    document.getElementById('ajuste-arch-msg').innerHTML='<span style="color:red;">Error: '+e.message+'</span>';
    setTimeout(function(){cerrarAjuste();},3000);
  }
}
function cerrarAjuste(){document.getElementById('modal-ajuste').style.display='none';['ajuste-msg','ajuste-smin-msg','ajuste-consumo-msg','ajuste-arch-msg'].forEach(function(id){var el=document.getElementById(id);if(el)el.innerHTML='';});}
function abrirSolIdx(ri){
  var a=(window._alertasData||[])[ri];if(!a)return;
  abrirSolicitudCompra(a.codigo_mp,a.nombre,a.deficit);
}
var _solMP={};
function abrirSolicitudCompra(cod,nom,deficit){
  _solMP={cod:cod,nom:nom,deficit:deficit};
  document.getElementById("modal-solicitud-compra").style.display="flex";
  document.getElementById("sol-mp-info").textContent=cod+" - "+nom+" | Deficit: "+deficit.toLocaleString()+"g";
  document.getElementById("sol-cantidad").value=deficit>0?deficit:"";
  document.getElementById("sol-nombre").value=OPER_ACTUAL||"";
  document.getElementById("sol-msg").innerHTML="";
}
function cerrarSolicitudCompra(){
  document.getElementById("modal-solicitud-compra").style.display="none";
}
async function enviarSolicitudCompra(){
  var nom=document.getElementById("sol-nombre").value.trim();
  var cant=parseFloat(document.getElementById("sol-cantidad").value);
  if(!nom){alert("Escribe tu nombre");return;}
  if(!cant||cant<=0){alert("Ingresa una cantidad valida");return;}
  var data={solicitante:nom,urgencia:document.getElementById("sol-urgencia").value,observaciones:document.getElementById("sol-obs").value,
    items:[{codigo_mp:_solMP.cod,nombre_mp:_solMP.nom,cantidad_g:cant,unidad:"g",justificacion:"Solicitud desde alertas de stock"}]};
  try{
    var r=await fetch("/api/solicitudes-compra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      document.getElementById("sol-msg").innerHTML='<div class="alert-success">&#10003; Solicitud '+res.numero+' creada correctamente.</div>';
      setTimeout(function(){cerrarSolicitudCompra();},3000);
    } else { document.getElementById("sol-msg").innerHTML='<div class="alert-error">Error al crear solicitud</div>'; }
  }catch(e){ document.getElementById("sol-msg").innerHTML='<div class="alert-error">Error de conexion</div>'; }
}
function cerrarHistorial(){document.getElementById('modal-historial').style.display='none';}
async function verHistorialLote(idx){
  var i=_lotes[idx];if(!i)return;
  document.getElementById('modal-historial').style.display='flex';
  document.getElementById('hist-lote-info').textContent=i.material_id+' - '+i.material_nombre+' Lote:'+(i.lote||'S/L')+' Stock:'+i.cantidad_g+'g';
  var tb=document.getElementById('hist-lote-body');
  tb.innerHTML='<tr><td colspan=4 style=text-align:center>Cargando...</td></tr>';
  try{
    var r=await fetch('/api/movimientos'),d=await r.json();
    var mv=(d.movimientos||[]).filter(function(m){return m.lote===i.lote&&m.material_id===i.material_id;});
    if(!mv.length){tb.innerHTML='<tr><td colspan=5 style=text-align:center>Sin movimientos</td></tr>';return;}
    tb.innerHTML=mv.map(function(m){var f=m.fecha?m.fecha.substring(0,16).replace("T"," "):"";return "<tr><td>"+m.tipo+"</td><td>"+m.cantidad+"</td><td>"+f+"</td><td>"+(m.observaciones||"")+"</td><td>"+(m.operador||"")+"</td></tr>";}).join("");
  }catch(e){tb.innerHTML='<tr><td colspan=5>Error</td></tr>';}
}

async function confirmarAjuste(){
  var fis=parseFloat(document.getElementById('ajuste-fisico').value);
  if(isNaN(fis)||fis<0){alert('Cantidad inválida');return;}
  var dif=Math.round((fis-_ajDat.sa)*100)/100;
  if(dif===0){alert('El stock físico coincide con el sistema');return;}
  var tipo=dif>0?'Entrada':'Salida';
  var obs='AJUSTE: '+(document.getElementById('ajuste-obs').value||'Conteo físico')+' | Op: '+OPER_ACTUAL;
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({material_id:_ajDat.mid,material_nombre:_ajDat.mn,
        cantidad:Math.abs(dif),tipo:tipo,observaciones:obs,lote:_ajDat.lt,operador:OPER_ACTUAL})});
    var res=await r.json();
    var sg=dif>0?'+':'';
    document.getElementById('ajuste-msg').innerHTML='<div class="alert-success">✓ Ajuste registrado: '+sg+dif.toLocaleString()+'g ('+tipo+'). Stock actualizado.</div>';
    setTimeout(function(){cerrarAjuste();loadStock();},2500);
  }catch(e){document.getElementById('ajuste-msg').innerHTML='<div class="alert-error">Error al registrar ajuste</div>';}
}

async function exportarExcelStock(){
  var r=await fetch('/api/lotes'),d=await r.json(),L=d.lotes||[];
  if(!L.length){alert('Sin datos');return;}
  var h='Codigo,Nombre,Lote,Cantidad_g,Estanteria,Posicion,FechaVenc,Estado';
  var rows=L.map(function(i){return [i.material_id,i.material_nombre,i.lote,i.cantidad_g,i.estanteria,i.posicion,i.fecha_vencimiento,i.alerta].join(',');});
  dlCSV('Stock_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
async function exportarExcelMovimientos(){
  var r=await fetch('/api/movimientos'),d=await r.json(),M=d.movimientos||[];
  if(!M.length){alert('Sin movimientos');return;}
  var h='Material,Cantidad_g,Tipo,Fecha,Observaciones,Operador';
  var rows=M.map(function(m){return [m.material_nombre,m.cantidad,m.tipo,m.fecha,(m.observaciones||'').replace(/,/g,';'),m.operador||''].join(',');});
  dlCSV('Movimientos_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
async function exportarExcelProducciones(){
  var r=await fetch('/api/produccion'),d=await r.json(),P=d.producciones||[];
  if(!P.length){alert('Sin producciones');return;}
  var h='Producto,Cantidad_kg,Fecha,Operador,Estado';
  var rows=P.map(function(p){return [p.producto,p.cantidad,p.fecha,p.operador||'',p.estado].join(',');});
  dlCSV('Producciones_'+fhoy()+'.csv',[h].concat(rows).join(String.fromCharCode(10)));
}
function fhoy(){var d=new Date();return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate();}
function dlCSV(n,csv){
  var b=new Blob([csv],{type:'text/csv'});
  var u=URL.createObjectURL(b);
  var a=document.createElement('a');
  a.href=u;a.download=n;
  document.body.appendChild(a);a.click();
  document.body.removeChild(a);URL.revokeObjectURL(u);
}
function descargarCSV(nombre,cols,rows){
  var sep=',';
  var lines=[cols.join(sep)];
  rows.forEach(function(r){
    lines.push(r.map(function(c){
      var s=c==null?'':String(c);
      if(s.indexOf(',')>=0||s.indexOf('"')>=0){s='"'+s.replace(/"/g,'""')+'"';}
      return s;
    }).join(sep));
  });
  var csv=lines.join(String.fromCharCode(10));
  var blob=new Blob([csv],{type:'text/csv'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a');
  a.href=url;a.download=nombre;
  document.body.appendChild(a);a.click();document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function cargarHistProd(){
  try{
    var r=await fetch('/api/produccion'),d=await r.json();
    var ps=d.producciones||[];
    var tb=document.getElementById('hist-prod-body');
    if(!tb)return;
    if(!ps.length){tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;padding:16px;">Sin producciones registradas</td></tr>';return;}
    tb.innerHTML=ps.map(function(p){
      var f=p.fecha?p.fecha.substring(0,16).replace('T',' '):'';
      var op=p.operador||'<span style="color:#bbb;font-style:italic;">-</span>';
      return '<tr><td style="font-weight:600;">'+p.producto+'</td><td style="text-align:right;font-weight:700;color:#2B7A78;">'+p.cantidad.toLocaleString()+' kg</td><td style="font-size:0.85em;color:#666;">'+f+'</td><td>'+op+'</td><td style="text-align:center;"><span style="background:#d4edda;color:#155724;padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:600;">'+p.estado+'</span></td></tr>';
    }).join('');
  }catch(e){}
}


function switchTab(n,btn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('.sub-tab-bar').forEach(function(b){b.classList.remove('visible');});
  document.getElementById(n).classList.add('active');
  if(btn) btn.classList.add('active');
  if(n==='stock') loadStock();
  if(n==='formulas'||n==='produccion') loadFormulas();
  if(n==='cuarentena') cargarCuarentena();
  if(n==='ingreso') initIngreso();
  if(n==='abc') loadABC();
  if(n==='conteo'){ cargarEstanterias(); cargarHistorialConteos(); cargarProgramacionCiclica(); }
  if(n==='empaque'){ cargarMeeAlertas(); cargarMeeStock(); cargarMeeHistorial(); }
  if(n==='alertas'){ loadAlertas(); loadAlertasReabas(); loadVenc30(); loadAlertasMEE(); }
  if(n==='stock') loadMEE();
  if(n==='acondicionamiento') loadAcond();
  if(n==='liberacion') loadLiberaciones('');
  if(n==='movimientos') loadMovimientos();
  if(n==='produccion') cargarHistProd();
  if(n==='movimientos') loadMovimientos();
}


function switchGroup(barId,defaultTab,mainBtn){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-button').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('.sub-tab-bar').forEach(function(b){b.classList.remove('visible');});
  if(mainBtn) mainBtn.classList.add('active');
  var bar=document.getElementById(barId);
  if(bar){ bar.classList.add('visible'); bar.querySelectorAll('.sub-btn').forEach(function(b){b.classList.remove('active');}); bar.querySelectorAll('.sub-btn').forEach(function(b){ if(b.getAttribute('onclick')&&b.getAttribute('onclick').indexOf("'"+defaultTab+"'")>=0) b.classList.add('active'); }); }
  subSwitchTab(defaultTab,null,barId);
}
function subSwitchTab(tabId,btn,barId){
  document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active');});
  var bar=document.getElementById(barId);
  if(bar){ bar.querySelectorAll('.sub-btn').forEach(function(b){b.classList.remove('active');}); }
  if(btn) btn.classList.add('active');
  var target=document.getElementById(tabId);
  if(target) target.classList.add('active');
  if(tabId==='stock'){loadStock();loadMEE();}
  if(tabId==='formulas'||tabId==='produccion') loadFormulas();
  if(tabId==='produccion') cargarHistProd();
  if(tabId==='cuarentena') cargarCuarentena();
  if(tabId==='ingreso') initIngreso();
  if(tabId==='abc') loadABC();
  if(tabId==='conteo'){ cargarEstanterias(); cargarHistorialConteos(); cargarProgramacionCiclica(); }
  if(tabId==='alertas'){ loadAlertas(); loadAlertasReabas(); loadVenc30(); loadAlertasMEE(); }
  if(tabId==='movimientos') loadMovimientos();
}
var _charts={};
async function loadDashboard(){
  try{
    var r=await fetch('/api/inventario'), d=await r.json();
    document.getElementById('stock-total').textContent=((d.stock_total||0)/1000).toFixed(1)+' kg';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    document.getElementById('producciones-count').textContent=d.producciones||'0';
    fetch('/api/alertas-reabastecimiento').then(function(r2){return r2.json();}).then(function(ar){
      var n=ar.alertas?ar.alertas.length:0;
      var el=document.getElementById('alertas-count');
      if(el) el.textContent=n>0?n+' alertas!':'OK';
      var panel=document.getElementById('dash-alertas-rapidas');
      if(panel&&n>0){
        panel.style.display='block';
        var lista=document.getElementById('dash-alertas-lista');
        if(lista) lista.innerHTML=ar.alertas.slice(0,3).map(function(a){
          return '<div style="margin-bottom:4px;"><b>'+a.codigo_mp+'</b> '+a.nombre+' - Stock: '+a.stock_actual.toLocaleString()+'g / Min: '+a.stock_minimo.toLocaleString()+'g <span style="color:#cc0000;font-weight:700;">Deficit: '+a.deficit.toLocaleString()+'g</span></div>';
        }).join('')+(n>3?'<div style="color:#888;font-size:0.85em;">... y '+(n-3)+' mas</div>':'');
      } else if(panel){ panel.style.display='none'; }
    }).catch(function(){});
  }catch(e){ console.error(e); }
}

async function loadDashboardCompleto(){
  loadDashboard();
  try{
    var r=await fetch('/api/dashboard-stats'), d=await r.json();
    var estados=d.estados_lotes||{};
    var ev=document.getElementById('dash-vencidos'); if(ev) ev.textContent=estados.VENCIDO||0;
    var ec=document.getElementById('dash-criticos'); if(ec) ec.textContent=estados.CRITICO||0;
    var ep=document.getElementById('dash-proximos'); if(ep) ep.textContent=estados.PROXIMO||0;
    var venc=d.vencimientos_por_mes||{}; var meses=Object.keys(venc);
    var ctx1=document.getElementById('chart-vencimientos');
    if(ctx1){
      if(_charts.venc){ _charts.venc.destroy(); }
      var emp=document.getElementById('chart-venc-empty');
      if(meses.length>0){
        ctx1.style.display='block'; if(emp) emp.style.display='none';
        _charts.venc=new Chart(ctx1.getContext('2d'),{
          type:'bar',
          data:{labels:meses,datasets:[{label:'Kg que vencen',data:meses.map(function(m){return venc[m].kg;}),
            backgroundColor:meses.map(function(m,i){return i===0?'rgba(204,0,0,0.7)':i<=1?'rgba(230,81,0,0.7)':'rgba(245,127,23,0.7)';}),borderRadius:4}]},
          options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx1.style.display='none'; if(emp) emp.style.display='block'; }
    }
    var top=d.top_stock||[]; var ctx2=document.getElementById('chart-top-stock');
    if(ctx2){
      if(_charts.top){ _charts.top.destroy(); }
      var emp2=document.getElementById('chart-stock-empty');
      if(top.length>0){
        ctx2.style.display='block'; if(emp2) emp2.style.display='none';
        _charts.top=new Chart(ctx2.getContext('2d'),{
          type:'bar',
          data:{labels:top.map(function(t){return t.nombre.length>18?t.nombre.substring(0,16)+'...':t.nombre;}),
            datasets:[{label:'Stock (kg)',data:top.map(function(t){return t.kg;}),backgroundColor:'rgba(102,126,234,0.7)',borderRadius:4}]},
          options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,title:{display:true,text:'kg'}}}}
        });
      } else { ctx2.style.display='none'; if(emp2) emp2.style.display='block'; }
    }
  }catch(e){ console.error('Stats error:',e); }
}

async function loadStock(){
  try{
    var r=await fetch('/api/lotes'), d=await r.json();
    _lotes=d.lotes||[];
    document.getElementById('stock-count').textContent=_lotes.length+' lotes';
    renderStock(_lotes);
  }catch(e){
    document.getElementById('stock-body').innerHTML='<tr><td colspan="13" style="padding:20px;color:#c00;">Error al cargar.</td></tr>';
  }
}
function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="13" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
  var bg={vencido:'#ffebeb',critico:'#fff3e0',proximo:'#fffde7',ok:'transparent'};
  var fc={vencido:'#cc0000',critico:'#e65100',proximo:'#f57f17',ok:'#1a8a1a'};
  var lb={vencido:'VENCIDO',critico:'CRITICO',proximo:'PROXIMO',ok:'VIGENTE'};
  var h='';
  items.forEach(function(i,idx){ var gi=_lotes.indexOf(i); if(gi<0)gi=idx;
    var a=i.alerta||'ok';
    var qc=i.cantidad_g<=0?'color:#cc0000;font-weight:700;':i.cantidad_g<500?'color:#e68a00;font-weight:700;':'color:#1a8a1a;font-weight:700;';
    var bajo_min=i.stock_min_g>0&&i.cantidad_g<i.stock_min_g;
    var min_style=bajo_min?'background:#ffebeb;color:#cc0000;font-weight:700;':'';
    var dias=i.dias_para_vencer!=null?i.dias_para_vencer:'';
    var dc=i.dias_para_vencer!=null&&i.dias_para_vencer<0?'color:#cc0000;font-weight:700;':i.dias_para_vencer<=30?'color:#e65100;font-weight:700;':'';
    h+='<tr style="background:'+bg[a]+';font-size:0.83em;">';
    h+='<td style="font-family:monospace;color:#555;">'+i.material_id+'</td>';
    h+='<td style="color:#444;font-size:0.82em;">'+i.nombre_inci+'</td>';
    h+='<td style="font-weight:600;">'+i.material_nombre+'</td>';
    h+='<td style="color:#888;">'+i.tipo+'</td>';
    h+='<td style="color:#555;">'+i.proveedor+'</td>';
    h+='<td style="text-align:right;'+min_style+'">'+i.stock_min_g.toLocaleString()+'</td>';
    h+='<td style="font-family:monospace;">'+i.lote+'</td>';
    h+='<td style="text-align:right;'+qc+'">'+i.cantidad_g.toLocaleString()+'</td>';
    h+='<td style="text-align:center;font-weight:700;color:#667eea;">'+i.estanteria+'</td>';
    h+='<td style="text-align:center;">'+i.posicion+'</td>';
    h+='<td style="text-align:center;color:'+fc[a]+';">'+i.fecha_vencimiento+'</td>';
    h+='<td style="text-align:right;'+dc+'">'+dias+'</td>';
    h+='<td style="text-align:center;"><span style="background:'+bg[a]+';color:'+fc[a]+';padding:2px 7px;border-radius:10px;font-weight:700;font-size:0.78em;border:1px solid '+fc[a]+';">'+lb[a]+'</span></td>';
    h+='<td style="text-align:center;"><button onclick="abrirAjusteIdx('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#f0ad4e;color:#fff;border-radius:4px;">Ajustar</button></td>';
    h+='<td style="text-align:center;"><button onclick="verHistorialLote('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#667eea;color:#fff;border-radius:4px;">Historial</button></td>';
    h+='</tr>';
  });
  tb.innerHTML=h;
}
function filterStock(){
  var q=document.getElementById('stock-search').value.toLowerCase();
  var f=_lotes.filter(function(i){
    return !q||(i.material_id.toLowerCase().includes(q)||i.material_nombre.toLowerCase().includes(q)||
               i.nombre_inci.toLowerCase().includes(q)||(i.lote||'').toLowerCase().includes(q)||
               (i.proveedor||'').toLowerCase().includes(q));
  });
  document.getElementById('stock-count').textContent=f.length+' de '+_lotes.length;
  renderStock(f);
}

async function initIngreso(){
  if(Object.keys(_cat).length===0){
    try{var r=await fetch('/api/maestro-mps'),d=await r.json();(d.mps||[]).forEach(function(mp){_cat[mp.codigo_mp]=mp;});}catch(e){}
  }
  cargarHistIngreso();
}
function ocultarDropMP(){var d=document.getElementById('mp-dropdown');if(d)d.style.display='none';}
function seleccionarMP(mp){
  document.getElementById('ing-cod').value=mp.codigo_mp;
  document.getElementById('ing-inci').value=mp.nombre_inci||'';
  document.getElementById('ing-nombre').value=mp.nombre_comercial||'';
  document.getElementById('ing-tipo').value=mp.tipo||'';
  var p=document.getElementById('ing-prov');if(p&&!p.value)p.value=mp.proveedor||'';
  var st=document.getElementById('ing-status');
  if(st){st.textContent='✓ '+mp.nombre_comercial+' ('+mp.codigo_mp+')';st.style.color='#27ae60';}
  var panel=document.getElementById('ing-nueva-mp-inline');if(panel)panel.style.display='none';
  ocultarDropMP();
}
async function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  try{
    var r2=await fetch('/api/maestro-mps'),d2=await r2.json(),mps=d2.mps||[];
    var busq=val.toLowerCase();
    var matches=mps.filter(function(m){
      return (m.codigo_mp||'').toLowerCase().includes(busq)||(m.nombre_comercial||'').toLowerCase().includes(busq)||(m.nombre_inci||'').toLowerCase().includes(busq);
    }).slice(0,12);
    window._mpMatches=matches;
    if(dd){
      if(!matches.length){dd.style.display='none';}
      else{
        dd.style.display='block';
        dd.innerHTML=matches.map(function(m,i){return '<div class="mp-item" style="padding:9px 14px;cursor:pointer;border-bottom:1px solid #eee;font-size:0.9em;" onmousedown="seleccionarMP(_mpMatches['+i+'])">'+'<span style="font-family:monospace;color:#667eea;font-size:0.85em;">'+m.codigo_mp+'</span> &mdash; <strong>'+m.nombre_comercial+'</strong>'+(m.proveedor?' <span style="color:#888;font-size:0.82em;">('+m.proveedor+')</span>':'')+'</div>';}).join('');
      }
    }
    var found=mps.find(function(m){return (m.codigo_mp||'').toLowerCase()===busq;});
    if(found){seleccionarMP(found);}
    else if(!matches.length){
      if(st){st.textContent='MP nueva — llena los datos';st.style.color='#e67e22';}
      if(panel)panel.style.display='block';
    } else {
      if(st){st.textContent='Selecciona una opcion de la lista';st.style.color='#667eea';}
    }
  }catch(e){if(st){st.textContent='Error buscando';st.style.color='#c0392b';}}
}


async function cargarOCsPendientes(){
  try{
    var r=await fetch('/api/ordenes-compra/pendientes-recepcion');
    if(!r.ok) return;
    var ocs=await r.json();
    var sel=document.getElementById('ing-oc-sel');
    if(!sel) return;
    // clear existing options except first placeholder
    while(sel.options.length>1) sel.remove(1);
    (ocs||[]).forEach(function(oc){
      (oc.items||[]).forEach(function(item){
        var opt=document.createElement('option');
        opt.value=oc.numero_oc+'|'+item.codigo_mp;
        var kg=(item.cantidad_pendiente_g/1000).toFixed(2);
        opt.textContent=oc.numero_oc+' — '+item.nombre_mp+' ('+kg+' kg pendientes)';
        opt.dataset.codigo=item.codigo_mp;
        opt.dataset.nombre=item.nombre_mp;
        opt.dataset.inci=item.nombre_inci||'';
        opt.dataset.proveedor=oc.proveedor||'';
        opt.dataset.precio=item.precio_unitario||'';
        sel.appendChild(opt);
      });
    });
  }catch(e){}
}
function autocompletarDesdeOC(){
  var sel=document.getElementById('ing-oc-sel');
  if(!sel||sel.selectedIndex<1) return;
  var opt=sel.options[sel.selectedIndex];
  if(!opt.dataset.codigo) return;
  var cod=document.getElementById('ing-cod');
  var nom=document.getElementById('ing-nombre');
  var inci=document.getElementById('ing-inci');
  var prov=document.getElementById('ing-prov');
  var precio=document.getElementById('ing-precio-kg');
  if(cod) cod.value=opt.dataset.codigo;
  if(nom) nom.value=opt.dataset.nombre||'';
  if(inci) inci.value=opt.dataset.inci||'';
  if(prov) prov.value=opt.dataset.proveedor||'';
  if(precio && opt.dataset.precio) precio.value=opt.dataset.precio;
  // trigger lookup & valor total
  if(cod) cod.dispatchEvent(new Event('input'));
  calcularValorTotal();
}
function calcularValorTotal(){
  var cant=parseFloat(document.getElementById('ing-cant')?document.getElementById('ing-cant').value:0)||0;
  var precio=parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0;
  var vt=document.getElementById('ing-valor-total');
  if(!vt) return;
  var val=(cant/1000)*precio;
  vt.value=val>0?'$'+val.toLocaleString('es-CO',{maximumFractionDigits:0}):'';
}
async function registrarIngreso(){
  var cod=(document.getElementById('ing-cod').value||'').toUpperCase().trim();
  var cant=parseFloat(document.getElementById('ing-cant').value)||0;
  if(!cod){alert('Ingresa el codigo MP');return;}
  if(cant<=0){alert('Ingresa una cantidad valida');return;}
  var esNueva=document.getElementById('ing-nueva-mp-inline')&&document.getElementById('ing-nueva-mp-inline').style.display!=='none';
  var ocSel=document.getElementById('ing-oc-sel');
  var ocVal=ocSel&&ocSel.value?ocSel.value:'';
  var numOC=ocVal?ocVal.split('|')[0]:'';
  var enCuarentena=document.getElementById('ing-cuarentena')&&document.getElementById('ing-cuarentena').checked;
  var data={codigo_mp:cod,nombre_comercial:document.getElementById('ing-nombre').value||'',
    lote:document.getElementById('ing-lote').value||'',cantidad:cant,operador:OPER_ACTUAL,
    fecha_vencimiento:document.getElementById('ing-vence').value||'',
    estanteria:document.getElementById('ing-est').value||'',
    posicion:document.getElementById('ing-pos').value||'',
    proveedor:document.getElementById('ing-prov').value||'',
    observaciones:document.getElementById('ing-obs').value||'',
    precio_kg:parseFloat(document.getElementById('ing-precio-kg')?document.getElementById('ing-precio-kg').value:0)||0,
    numero_factura:document.getElementById('ing-factura')?document.getElementById('ing-factura').value.trim():'',
    numero_oc:numOC,
    cuarentena:enCuarentena};
  if(esNueva){
    data.nombre_inci=document.getElementById('ing-inci-new')?document.getElementById('ing-inci-new').value:'';
    data.tipo=document.getElementById('ing-tipo-new')?document.getElementById('ing-tipo-new').value:'';
    data.stock_minimo=parseFloat(document.getElementById('ing-smin-new')?document.getElementById('ing-smin-new').value:0)||0;
  }
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      document.getElementById('ing-msg').innerHTML='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA activa':'')+'</div>';
      await cargarHistIngreso();
      await cargarOCsPendientes();
    } else {document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error')+'</div>';}
  }catch(e){document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}
function generarRotuloIngreso(){
  if(!_ultimoIng){alert('Registra un ingreso primero');return;}
  window.open('/rotulo-recepcion/'+encodeURIComponent(_ultimoIng.codigo)+'/'+encodeURIComponent(_ultimoIng.lote||'SL')+'/'+(parseFloat(_ultimoIng.cantidad)||0).toFixed(1),'_blank');
}
function limpiarIngreso(){
  ['ing-cod','ing-inci','ing-nombre','ing-tipo','ing-prov','ing-lote','ing-cant','ing-vence','ing-est','ing-pos','ing-obs','ing-factura','ing-precio-kg','ing-valor-total'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
  var ocSel=document.getElementById('ing-oc-sel');if(ocSel)ocSel.selectedIndex=0;
  var cuar=document.getElementById('ing-cuarentena');if(cuar)cuar.checked=false;
  ocultarFormNuevaMP();
  var st=document.getElementById('ing-status');if(st){st.textContent='';st.style.color='#667eea';}
  document.getElementById('ing-msg').innerHTML='';
}
async function cargarHistIngreso(){
  try{
    var r=await fetch('/api/movimientos'),d=await r.json();
    var entradas=(d.movimientos||[]).filter(function(m){return m.tipo==='Entrada';}).slice(0,20);
    var tb=document.querySelector('#ing-hist tbody'); if(!tb) return;
    if(!entradas.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin entradas</td></tr>';return;}
    var h='';
    entradas.forEach(function(m){
      h+='<tr><td style="font-family:monospace;font-size:0.85em;">'+(m.material_id||'')+'</td>';
      var cat=_cat[m.material_id]||{};
      h+='<td style="font-size:0.8em;color:#444;">'+(cat.nombre_inci||'')+'</td>';
      h+='<td>'+m.material_nombre+'</td>';
      h+='<td style="font-family:monospace;">'+(m.lote||'')+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+m.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(m.proveedor||'')+'</td>';
      h+='<td style="color:#c0392b;font-size:0.85em;">'+(m.fecha_vencimiento?m.fecha_vencimiento.substring(0,10):'')+'</td>';
      h+='<td style="font-size:0.82em;color:#888;">'+m.fecha.substring(0,10)+'</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){}
}
function togglePTFields(){
  var checked=document.getElementById('prod-pt-check').checked;
  var fields=document.getElementById('prod-pt-fields');
  if(fields) fields.style.display=checked?'block':'none';
}
function abrirRotulos(){
  var prod=document.getElementById('prod-sel')?document.getElementById('prod-sel').value:'';
  var manual=document.getElementById('prod-manual')?document.getElementById('prod-manual').value.trim():'';
  var producto=prod||manual;
  var kg=parseFloat(document.getElementById('prod-kg')?document.getElementById('prod-kg').value:0)||0;
  if(!producto){alert('Selecciona un producto primero');return;}
  if(kg<=0){alert('Ingresa la cantidad en kg');return;}
  window.open('/rotulos/'+encodeURIComponent(producto)+'/'+(parseFloat(kg)||0).toFixed(1),'_blank');
}

async function loadFormulas(){
  try{
    var r=await fetch('/api/formulas'), d=await r.json();
    fData=d.formulas||[];
    renderFormulas(fData);
    var sel=document.getElementById('prod-sel');
    if(sel){
      var cur=sel.value;
      sel.innerHTML='<option value="">-- Selecciona un producto --</option>';
      fData.forEach(function(f){var o=document.createElement('option');o.value=f.producto_nombre;o.textContent=f.producto_nombre;sel.appendChild(o);});
      sel.value=cur;
    }
  }catch(e){}
}

function renderFormulas(fl){
  var c=document.getElementById('formulas-list'); if(!c) return;
  if(!fl.length){c.innerHTML='<p style="color:#999;">Sin formulas aun.</p>';return;}
  var html='';
  fl.forEach(function(f,idx){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    var ok=Math.abs(total-100)<0.1;
    var rows='';
    f.items.forEach(function(it){
      rows+='<tr><td style="font-family:monospace;">'+it.material_id+'</td><td>'+it.material_nombre+'</td><td>'+it.porcentaje+'%</td><td style="font-weight:600;">'+(it.porcentaje*10).toFixed(2)+'g</td></tr>';
    });
    html+='<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:12px;background:white;">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">';
    html+='<h4 style="color:#667eea;">'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g)</span></h4>';
    html+='<div style="display:flex;gap:6px;">';
    html+='<button onclick="editFormula('+idx+')" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>';
    html+='<button onclick="delFormula('+idx+')" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>';
    html+='</div></div>';
    html+='<table class="table" style="font-size:0.85em;"><thead><tr><th>Codigo MP</th><th>Material</th><th>%</th><th>g/kg</th></tr></thead><tbody>'+rows+'</tbody></table>';
    html+='<small style="color:'+(ok?'#28a745':'#e68a00')+';">Total: '+total.toFixed(2)+'%'+(ok?' OK':' revisar')+'</small>';
    html+='</div>';
  });
  c.innerHTML=html;
}

function addFRow(){
  var div=document.createElement('div');
  div.style.cssText='display:grid;grid-template-columns:140px 1fr 90px 38px;gap:6px;margin-bottom:6px;';
  div.innerHTML='<input type="text" placeholder="MP00001" class="fi-id" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="text" placeholder="Nombre material" class="fi-nm" style="padding:7px;border:1px solid #ddd;border-radius:5px;">'
    +'<input type="number" placeholder="%" step="0.001" class="fi-pc" style="padding:7px;border:1px solid #ddd;border-radius:5px;" oninput="calcPct()">'
    +'<button onclick="this.parentElement.remove();calcPct();" style="background:#ff4444;color:white;border:none;border-radius:5px;cursor:pointer;padding:7px;font-size:0.9em;">x</button>';
  document.getElementById('fi-container').appendChild(div);
}

function calcPct(){
  var t=Array.from(document.querySelectorAll('.fi-pc')).reduce(function(s,i){return s+(parseFloat(i.value)||0);},0);
  var el=document.getElementById('pct-total');
  el.textContent='Total: '+t.toFixed(2)+'%';
  el.style.color=Math.abs(t-100)<0.1?'#28a745':(t>100?'#cc0000':'#e68a00');
}

async function guardarFormula(){
  var prod=document.getElementById('formula-producto').value.trim();
  if(!prod){alert('Ingresa el nombre del producto');return;}
  var base=parseFloat(document.getElementById('formula-base').value)||1000;
  var desc=document.getElementById('formula-desc').value.trim();
  var rows=document.querySelectorAll('#fi-container > div');
  var items=[];
  rows.forEach(function(row){
    var id=row.querySelector('.fi-id').value.trim();
    var nm=row.querySelector('.fi-nm').value.trim();
    var pc=parseFloat(row.querySelector('.fi-pc').value)||0;
    if(id&&nm&&pc>0) items.push({material_id:id,material_nombre:nm,porcentaje:pc});
  });
  if(!items.length){alert('Agrega al menos un ingrediente');return;}
  try{
    var r=await fetch('/api/formulas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto_nombre:prod,unidad_base_g:base,descripcion:desc,items:items})});
    var res=await r.json();
    document.getElementById('formula-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    await loadFormulas();
    setTimeout(function(){document.getElementById('formula-msg').innerHTML='';},3000);
  }catch(e){document.getElementById('formula-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

function editFormula(idx){
  var f=fData[idx]; if(!f) return;
  document.getElementById('formula-producto').value=f.producto_nombre;
  document.getElementById('formula-base').value=f.unidad_base_g;
  document.getElementById('formula-desc').value=f.descripcion||'';
  document.getElementById('fi-container').innerHTML='';
  f.items.forEach(function(item){
    addFRow();
    var rows=document.getElementById('fi-container').querySelectorAll('div');
    var row=rows[rows.length-1];
    row.querySelector('.fi-id').value=item.material_id;
    row.querySelector('.fi-nm').value=item.material_nombre;
    row.querySelector('.fi-pc').value=item.porcentaje;
  });
  calcPct();
  document.getElementById('formula-producto').scrollIntoView({behavior:'smooth'});
}

async function delFormula(idx){
  var nombre=fData[idx]?fData[idx].producto_nombre:'';
  if(!nombre||!confirm('Eliminar formula de '+nombre+'?')) return;
  await fetch('/api/formulas/'+encodeURIComponent(nombre),{method:'DELETE'});
  await loadFormulas();
}

function previewProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  var kg=parseFloat(document.getElementById('prod-kg').value)||0;
  var preview=document.getElementById('prod-preview');
  if(!prod||kg<=0){preview.style.display='none';return;}
  var f=fData.find(function(x){return x.producto_nombre===prod;});
  if(!f||!f.items.length){preview.style.display='none';return;}
  var g=kg*1000;
  document.getElementById('prod-preview-body').innerHTML=f.items.map(function(it){
    return '<tr><td>'+it.material_nombre+'</td><td style="text-align:right;font-weight:700;">'+((it.porcentaje/100)*g).toFixed(1)+' g</td></tr>';
  }).join('');
  preview.style.display='block';
}

async function registrarProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  if(!prod){alert('Ingresa un producto');return;}
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!kg||kg<=0){alert('Ingresa una cantidad valida');return;}
  try{
    var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad:kg,observaciones:document.getElementById('prod-obs').value,operador:OPER_ACTUAL})});
    var res=await r.json();
    var html='<div class="alert-success">'+res.message+'</div>';
    if(res.descuentos&&res.descuentos.length){
      html+='<div style="margin-top:8px;font-size:0.88em;color:#555;"><strong>MPs descontadas del inventario:</strong><ul style="margin-top:4px;padding-left:18px;">';
      res.descuentos.forEach(function(d){html+='<li>'+d.material+': '+d.cantidad_g.toLocaleString()+' g</li>';});
      html+='</ul></div>';
    }
    document.getElementById('prod-msg').innerHTML=html;
    document.getElementById('prod-preview').style.display='none';
    setTimeout(function(){
      document.getElementById('prod-sel').value='';
      document.getElementById('prod-manual').value='';
      document.getElementById('prod-kg').value='';
      document.getElementById('prod-obs').value='';
      document.getElementById('prod-msg').innerHTML='';
    },5000);
  }catch(e){document.getElementById('prod-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

async function loadABC(){
  try{
    var r=await fetch('/api/analisis-abc'), d=await r.json();
    var html='';
    if(d.items&&d.items.length){
      html='<div style="overflow-x:auto;"><table class="table"><thead><tr><th>Clase</th><th>Material</th><th>Stock (g)</th><th>% Acumulado</th></tr></thead><tbody>';
      d.items.forEach(function(i){
        var bg=i.clasificacion==='A'?'#28a745':i.clasificacion==='B'?'#fd7e14':'#6c757d';
        html+='<tr><td><span style="background:'+bg+';color:white;padding:3px 10px;border-radius:10px;font-weight:700;">'+i.clasificacion+'</span></td>'
          +'<td>'+i.material+'</td><td style="text-align:right;">'+Number(i.cantidad).toLocaleString()+'</td>'
          +'<td style="text-align:right;color:#667eea;">'+i.valor+'</td></tr>';
      });
      html+='</tbody></table></div>';
    } else { html='<p style="color:#999;">Sin datos de inventario para analizar</p>'; }
    document.getElementById('abc-results').innerHTML=html;
  }catch(e){document.getElementById('abc-results').innerHTML='<div class="alert-error">Error</div>';}
}

async function loadAlertas(){
  try{
    var r=await fetch('/api/alertas'), d=await r.json();
    var tb=document.querySelector('#alertas-table tbody');
    if(d.alertas&&d.alertas.length){
      tb.innerHTML=d.alertas.map(function(a){return '<tr><td>'+a.material_nombre+'</td><td>'+a.stock_actual+'</td><td>'+a.stock_minimo+'</td><td>'+a.estado+'</td><td style="font-size:0.85em;">'+a.fecha+'</td></tr>';}).join('');
    }else{tb.innerHTML='<tr><td colspan="5" style="text-align:center;color:#999;">Sin alertas</td></tr>';}
  }catch(e){}
}

async function loadMovimientos(){
  try{
    var r=await fetch('/api/movimientos'), d=await r.json();
    var tb=document.querySelector('#mov-table tbody');
    if(d.movimientos&&d.movimientos.length){
      tb.innerHTML=d.movimientos.map(function(m){
        var t=m.tipo==='Entrada'?'<span style="color:#28a745;font-weight:600;">Entrada</span>':'<span style="color:#cc4444;font-weight:600;">Salida</span>';
        var esAnulado=m.observaciones&&m.observaciones.indexOf('[ANULADO]')===0;
        var btnAnular=esAnulado
          ?'<span style="color:#aaa;font-size:0.8em;">Anulado</span>'
          :'<button onclick="anularMovimiento('+m.id+')" style="background:#cc4444;color:#fff;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:0.82em;">Anular</button>';
        return '<tr style="'+(esAnulado?'opacity:0.5;text-decoration:line-through;':'')+'">'+'<td>'+m.material_nombre+'</td>'+'<td style="text-align:right;">'+m.cantidad.toLocaleString()+'</td>'+'<td>'+t+'</td>'+'<td style="font-size:0.82em;color:#888;">'+m.fecha+'</td>'+'<td style="font-size:0.82em;color:#888;">'+m.observaciones+'</td>'+'<td>'+btnAnular+'</td>'+'</tr>';
      }).join('');
    }else{tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;">Sin movimientos</td></tr>';}
  }catch(e){}
}

async function anularMovimiento(movId){
  var motivo=prompt('Motivo de anulacion (obligatorio):');
  if(!motivo||!motivo.trim()){alert('Debes ingresar un motivo.');return;}
  try{
    var r=await fetch('/api/movimientos/'+movId+'/anular',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo.trim()})});
    var res=await r.json();
    if(res.ok){
      document.getElementById('mov-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
      loadMovimientos();
    }else{
      document.getElementById('mov-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al anular')+'</div>';
    }
  }catch(e){document.getElementById('mov-msg').innerHTML='<div class="alert-error">Error de conexion</div>';}
}

async function registrarMov(){
  var data={material_id:document.getElementById('mov-id').value,material_nombre:document.getElementById('mov-nombre').value,cantidad:parseFloat(document.getElementById('mov-cant').value),tipo:document.getElementById('mov-tipo').value,observaciones:document.getElementById('mov-obs').value};
  try{
    var r=await fetch('/api/movimientos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    document.getElementById('mov-msg').innerHTML='<div class="alert-success">'+res.message+'</div>';
    loadMovimientos();
  }catch(e){document.getElementById('mov-msg').innerHTML='<div class="alert-error">Error</div>';}
}

async function loadVenc30(){
  try{
    var r=await fetch('/api/lotes'),d=await r.json(),lotes=d.lotes||[];
    var prox=lotes.filter(function(l){return l.dias_para_vencer!=null&&l.dias_para_vencer>=0&&l.dias_para_vencer<=30;});
    var div=document.getElementById('venc30-content');if(!div)return;
    if(!prox.length){div.innerHTML='<span style="color:#28a745;font-weight:600;">Sin lotes proximos a vencer en 30 dias.</span>';return;}
    prox.sort(function(a,b){return a.dias_para_vencer-b.dias_para_vencer;});
    div.innerHTML='<table class="table" style="margin-top:8px;"><thead><tr><th>Codigo</th><th>Material</th><th>Lote</th><th style="text-align:right;">Cantidad(g)</th><th>Vence</th><th style="text-align:center;">Dias</th></tr></thead><tbody>'+
    prox.map(function(l){
      var c2=l.dias_para_vencer<=7?'color:#cc0000;font-weight:700;':'color:#e65100;font-weight:600;';
      return '<tr><td style="font-family:monospace;font-size:0.82em;">'+l.material_id+'</td><td style="font-weight:600;">'+l.material_nombre+'</td><td style="font-family:monospace;font-size:0.82em;">'+l.lote+'</td><td style="text-align:right;">'+l.cantidad_g.toLocaleString()+'</td><td>'+l.fecha_vencimiento+'</td><td style="text-align:center;'+c2+'">'+l.dias_para_vencer+'d</td></tr>';
    }).join('')+'</tbody></table>';
  }catch(e){}
}
async function loadAlertasReabas(){
  try{
    var r=await fetch('/api/alertas-reabastecimiento'), d=await r.json();
    var alertas=d.alertas||[];
    var tb=document.getElementById('reabas-body');
    if(!tb) return;
    if(!alertas.length){
      tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#28a745;padding:15px;">&#10003; Todo el stock esta sobre el minimo calculado</td></tr>';
      return;
    }
    var h='';
    window._alertasData=alertas;
    alertas.forEach(function(a,ri){
      var pct=a.stock_minimo>0?Math.round((a.stock_actual/a.stock_minimo)*100):0;
      var critico=pct<25;var urgente=pct>=25&&pct<50;
      var color=critico?'#ffebeb':urgente?'#fff3e0':'#fffde7';
      var badge=critico?'<span style="background:#cc0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">CRÍTICO</span>':
                urgente?'<span style="background:#e65100;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">URGENTE</span>':
                '<span style="background:#f57f17;color:white;padding:2px 8px;border-radius:10px;font-size:0.82em;font-weight:700;">BAJO</span>';
      var esMEE=a.tipo==='MEE';
      var tipoBadge=esMEE?'<span style="background:#2B7A78;color:white;padding:1px 7px;border-radius:8px;font-size:0.78em;font-weight:700;">MEE</span>':
                         '<span style="background:#555;color:white;padding:1px 7px;border-radius:8px;font-size:0.78em;font-weight:700;">MP</span>';
      var unidad=esMEE?'und':'g';
      h+='<tr style="background:'+color+';">';
      h+='<td style="text-align:center;">'+tipoBadge+'</td>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+a.codigo_mp+'</td>';
      h+='<td style="font-weight:600;">'+a.nombre+'</td>';
      h+='<td style="font-size:0.85em;color:#666;">'+a.proveedor+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+a.stock_minimo.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.stock_actual.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:right;color:#cc0000;font-weight:700;">'+a.deficit.toLocaleString()+' '+unidad+'</td>';
      h+='<td style="text-align:center;">'+badge+' '+pct+'%</td>';
      var accion=esMEE?'<button onclick="switchTab(&apos;mee&apos;,null)" style="padding:4px 10px;font-size:0.78em;background:#2B7A78;color:white;border-radius:4px;">Ver MEE</button>':
                       '<button onclick="abrirSolIdx('+ri+')" style="padding:4px 10px;font-size:0.78em;background:#2B7A78;color:white;border-radius:4px;">Solicitar</button>';
      h+='<td style="text-align:center;">'+accion+'</td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
  }catch(e){
    var tb2=document.getElementById('reabas-body');
    if(tb2) tb2.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;">Carga el catalogo maestro primero (python cargar_maestro.py)</td></tr>';
  }
}

/* ===== MEE FUNCTIONS ===== */
var MEE_CATS=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Frasco','Contorno','Otro'];

async function cargarSelectsMEE(){
  var r=await fetch('/api/mee/stock'); var d=await r.json();
  _meeData=d.items||[];
  filtrarMEEIngreso();
}
function filtrarMEEIngreso(){
  var cat=document.getElementById('mee-ing-cat').value;
  var sel=document.getElementById('mee-ing-cod');
  sel.innerHTML='<option value="">-- Selecciona --</option>';
  _meeData.filter(function(x){return !cat||x.categoria===cat;}).forEach(function(x){
    var o=document.createElement('option');o.value=x.codigo;o.textContent=x.codigo+' — '+x.descripcion;sel.appendChild(o);
  });
}
async function registrarIngresoMEE(){
  var cod=document.getElementById('mee-ing-cod').value;
  var cant=parseFloat(document.getElementById('mee-ing-cant').value);
  var ref=document.getElementById('mee-ing-ref').value;
  var obs=document.getElementById('mee-ing-obs').value;
  if(!cod||!cant){document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">Selecciona material y cantidad</span>';return;}
  var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,tipo:'Entrada',cantidad:cant,lote_ref:ref,observaciones:obs,responsable:OPER_ACTUAL})});
  var d=await r.json();
  if(r.ok){
    _ultimoMEE={codigo:cod,cant:cant,ref:ref};
    document.getElementById('mee-ing-msg').innerHTML='<span style="color:green;">Entrada registrada. Stock: '+d.stock_nuevo+' und &nbsp;<button onclick="generarRotuloMEE()" style="background:#2980b9;color:white;border:none;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.85em;">&#128209; Rotulo</button></span>';
    document.getElementById('btn-rotulo-mee').disabled=false;
    loadHistMEE();loadMEE();
  }else{document.getElementById('mee-ing-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
var _ultimoMEE=null;
function generarRotuloMEE(){
  if(!_ultimoMEE){alert('Primero registra una entrada MEE');return;}
  window.open('/rotulo-recepcion-mee/'+encodeURIComponent(_ultimoMEE.codigo)+'/'+(parseFloat(_ultimoMEE.cant)||0),'_blank');
}
function limpiarIngresoMEE(){document.getElementById('mee-ing-cod').value='';document.getElementById('mee-ing-cant').value='';document.getElementById('mee-ing-ref').value='';document.getElementById('mee-ing-obs').value='';}
async function loadHistMEE(){
  var r=await fetch('/api/mee/movimientos?tipo=Entrada&limit=20'); var d=await r.json();
  var tb=document.getElementById('mee-hist-body');
  if(!d.movimientos||!d.movimientos.length){tb.innerHTML='<tr><td colspan="7" style="text-align:center;color:#999;">Sin movimientos</td></tr>';return;}
  tb.innerHTML=d.movimientos.map(function(m){
    var col=m.tipo==='Entrada'?'#27ae60':m.tipo==='Ajuste'?'#f39c12':'#e74c3c';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.mee_codigo+'</td><td>'+m.descripcion+'</td><td><span style="color:'+col+';font-weight:600;">'+m.tipo+'</span></td><td style="text-align:right;font-weight:600;">'+m.cantidad+'</td><td>'+(m.lote_ref||'')+'</td><td>'+m.responsable+'</td><td>'+(m.fecha||'').substring(0,16)+'</td></tr>';
  }).join('');
}
async function loadMEE(){
  var cat=document.getElementById('mee-cat-filter')?document.getElementById('mee-cat-filter').value:'';
  var q=document.getElementById('mee-search')?document.getElementById('mee-search').value:'';
  var url='/api/mee/stock?';if(cat)url+='categoria='+encodeURIComponent(cat)+'&';if(q)url+='q='+encodeURIComponent(q);
  var r=await fetch(url); var d=await r.json();
  var tb=document.getElementById('mee-stock-body');
  if(!d.items||!d.items.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin materiales</td></tr>';return;}
  tb.innerHTML=d.items.map(function(m){
    var deficit=m.stock_actual-m.stock_minimo;
    var est=deficit<0?'<span style="color:#e74c3c;font-weight:700;">BAJO</span>':deficit<m.stock_minimo*0.3?'<span style="color:#f39c12;font-weight:700;">ALERTA</span>':'<span style="color:#27ae60;font-weight:700;">OK</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td><td><span style="font-size:11px;background:#f0f4ff;padding:2px 8px;border-radius:10px;">'+m.categoria+'</span></td><td>'+m.proveedor+'</td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;">'+m.stock_actual+'</td>'
    +'<td style="text-align:center;">'+est+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="abrirAjusteMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+')">Ajustar</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-ghost btn-sm" onclick="verHistorialMEE(&quot;'+m.codigo+'&quot;)">Hist.</button></td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
function abrirNuevoMEE(){document.getElementById('nuevo-mee-form').style.display='block';}
async function crearMEE(){
  var cod=document.getElementById('nmee-cod').value.trim().toUpperCase();
  var desc=document.getElementById('nmee-desc').value.trim();
  var cat=document.getElementById('nmee-cat').value;
  var prov=document.getElementById('nmee-prov').value.trim();
  var stock=parseFloat(document.getElementById('nmee-stock').value)||2000;
  var smin=parseFloat(document.getElementById('nmee-min').value)||1000;
  if(!cod||!desc){document.getElementById('nmee-msg').innerHTML='<span style="color:red;">Codigo y descripcion requeridos</span>';return;}
  var r=await fetch('/api/mee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,descripcion:desc,categoria:cat,proveedor:prov,stock_actual:stock,stock_minimo:smin})});
  var d=await r.json();
  if(r.ok){document.getElementById('nmee-msg').innerHTML='<span style="color:green;">Creado exitosamente</span>';document.getElementById('nuevo-mee-form').style.display='none';loadMEE();}
  else{document.getElementById('nmee-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';}
}
async function abrirAjusteMEE(cod,desc,stock){
  if(!OPER_ACTUAL){alert('Selecciona tu nombre primero');return;}
  var nuevo=prompt('Ajuste de stock: '+cod+' — '+desc+'\\nStock actual: '+stock+' und\\nNuevo valor:');
  if(nuevo===null||nuevo==='')return;
  var n=parseFloat(nuevo);if(isNaN(n)||n<0){alert('Valor invalido');return;}
  var obs=prompt('Motivo del ajuste:','Inventario fisico');
  var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codigo:cod,tipo:'Ajuste',cantidad:n,observaciones:obs||'Ajuste',responsable:OPER_ACTUAL})});
  var d=await r.json();
  if(d.ok){alert('Ajuste registrado. Stock: '+d.stock_nuevo+' und');loadMEE();}
  else alert('Error: '+(d.error||''));
}
async function verHistorialMEE(cod){
  var r=await fetch('/api/mee/movimientos?codigo='+encodeURIComponent(cod)+'&limit=30');
  var d=await r.json();
  var rows=d.movimientos||[];
  var html=rows.map(function(m){
    var col=m.tipo==='Entrada'?'#27ae60':m.tipo==='Ajuste'?'#f39c12':'#e74c3c';
    return '<tr style="border-bottom:1px solid #eee;"><td style="padding:6px;color:'+col+';font-weight:600;">'+m.tipo+'</td><td style="padding:6px;text-align:right;">'+m.cantidad+'</td><td style="padding:6px;color:#888;">'+m.referencia+'</td><td style="padding:6px;">'+m.operador+'</td><td style="padding:6px;font-size:0.82em;color:#666;">'+m.fecha+'</td></tr>';
  }).join('') || '<tr><td colspan="5" style="text-align:center;color:#999;padding:12px;">Sin movimientos</td></tr>';
  document.getElementById('hist-lote-info').textContent='MEE — '+cod+' ('+rows.length+' movimientos)';
  document.getElementById('hist-lote-body').innerHTML=html;
  document.getElementById('modal-historial').style.display='flex';
}
async function solicitarCompraMEE(cod,desc,stock,smin){
  var cant=prompt('Solicitar compra para: '+desc+'\\nStock actual: '+stock+' und / Minimo: '+smin+' und\\nCantidad a solicitar:');
  if(!cant||isNaN(parseFloat(cant)))return;
  var data={
    solicitante:OPER_ACTUAL||'Sistema',
    area:'Produccion',empresa:'Espagiria',categoria:'Envase y Empaque',tipo:'Compra',
    urgencia:'Urgente',observaciones:'Solicitud automatica desde alerta MEE',
    items:[{codigo_mp:cod,nombre_mp:desc,cantidad_g:parseFloat(cant),unidad:'und',valor_estimado:0}]
  };
  var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  var d=await r.json();
  if(r.ok)alert('Solicitud creada: '+d.numero+'\\nVisible en modulo Compras > Solicitudes');
  else alert('Error: '+(d.error||''));
}
async function loadAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  var tb=document.getElementById('mee-alertas-body');
  if(!d.alertas||!d.alertas.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:green;padding:16px;">Todo el stock MEE por encima del minimo</td></tr>';return;}
  tb.innerHTML=d.alertas.map(function(m){
    var def=m.stock_actual-m.stock_minimo;
    var niv=def<-m.stock_minimo?'<span style="color:#e74c3c;font-weight:700;">CRITICO</span>':'<span style="color:#f39c12;font-weight:700;">BAJO</span>';
    return '<tr><td style="font-family:monospace;font-size:11px;">'+m.codigo+'</td><td>'+m.descripcion+'</td>'
    +'<td><span style="background:#f0f4ff;padding:2px 8px;border-radius:10px;font-size:11px;">'+m.categoria+'</span></td>'
    +'<td style="text-align:right;">'+m.stock_minimo+'</td>'
    +'<td style="text-align:right;font-weight:700;color:#e74c3c;">'+m.stock_actual+'</td>'
    +'<td style="text-align:right;color:#e74c3c;font-weight:700;">'+def+'</td>'
    +'<td style="text-align:center;">'+niv+'</td>'
    +'<td style="text-align:center;"><button class="btn btn-sm" style="background:#4A6741;font-size:11px;" onclick="solicitarCompraMEE(&quot;'+m.codigo+'&quot;,&quot;'+_eq(m.descripcion)+'&quot;,'+m.stock_actual+','+m.stock_minimo+')">Solicitar</button></td>'
    +'</tr>';
  }).join('');
}
async function generarOCsDesdeAlertasMEE(){
  var r=await fetch('/api/alertas-mee'); var d=await r.json();
  if(!d.alertas||!d.alertas.length){alert('No hay alertas MEE activas');return;}
  var items=d.alertas.map(function(m){return {codigo_mp:m.codigo,nombre_mp:m.descripcion,cantidad_g:Math.max(m.stock_minimo*2-m.stock_actual,1),precio_unitario:0};});
  var r2=await fetch('/api/ordenes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:'Por asignar',observaciones:'OC automatica desde alertas MEE',items:items,creado_por:OPER_ACTUAL||'Sistema'})});
  var d2=await r2.json();
  if(r2.ok)alert('OC creada: '+d2.numero_oc+'\\nVisible en Compras > Ordenes');
  else alert('Error: '+(d2.error||''));
}
/* MEE en producción */
async function simularProduccion(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value.trim();
  var kg=parseFloat(document.getElementById('prod-kg').value);
  var panel=document.getElementById('prod-simul-result');
  if(!prod){panel.innerHTML='<span style="color:#e74c3c;">Selecciona un producto primero</span>';return;}
  if(!kg||kg<=0){panel.innerHTML='<span style="color:#e74c3c;">Ingresa la cantidad (kg) primero</span>';return;}
  panel.innerHTML='<span style="color:#667eea;">&#9203; Verificando stock y estimando costos...</span>';
  try{
    var r=await fetch('/api/produccion/simular',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad_kg:kg})});
    var d=await r.json();
    if(!r.ok){panel.innerHTML='<span style="color:#e74c3c;">'+(d.error||'Error al simular')+'</span>';return;}
    var bg=d.factible?'#f0fff4':'#fff5f5';
    var brd=d.factible?'#28a745':'#dc3545';
    var ico=d.factible?'&#9989;':'&#10060;';
    var titulo=d.factible
      ?'Stock suficiente para '+d.cantidad_kg+'kg de '+d.producto
      :d.faltantes+' ingrediente(s) insuficiente(s) para producir '+d.cantidad_kg+'kg';
    var rows=d.ingredientes.map(function(i){
      var rowbg=i.suficiente?'':'#fff0f0';
      var badge=i.suficiente
        ?'<span style="color:#28a745;font-weight:700;">OK</span>'
        :'<span style="color:#dc3545;font-weight:700;">FALTA '+i.g_faltante.toLocaleString()+'g</span>';
      var costoCell=i.precio_kg>0
        ?'<span style="color:#2d3748;">$'+Number(i.costo).toLocaleString('es-CO')+'</span>'
        :'<span style="color:#a0aec0;font-size:0.8em;">sin precio</span>';
      return '<tr style="background:'+rowbg+';">'
        +'<td>'+i.material_nombre+'</td>'
        +'<td style="text-align:right;">'+i.g_requerido.toLocaleString()+'g</td>'
        +'<td style="text-align:right;">'+i.g_disponible.toLocaleString()+'g</td>'
        +'<td style="text-align:right;">'+badge+'</td>'
        +'<td style="text-align:right;">'+costoCell+'</td></tr>';
    }).join('');
    var costoHtml='';
    if(d.costo_total>0){
      costoHtml='<div style="margin-top:10px;padding:10px 14px;background:#eef2ff;border-radius:8px;display:flex;gap:20px;flex-wrap:wrap;align-items:center;">'
        +'<span>&#128176; <strong>Costo estimado batch:</strong> $'+Number(d.costo_total).toLocaleString('es-CO')+'</span>'
        +'<span>&#128197; <strong>Costo/kg:</strong> $'+Number(d.costo_por_kg).toLocaleString('es-CO')+'</span>'
        +(d.ingredientes_sin_precio>0?'<span style="color:#e67e22;font-size:0.85em;">&#9888; '+d.ingredientes_sin_precio+' ingrediente(s) sin precio — costo subestimado ('+d.cobertura_precio_pct+'% cobertura)</span>':'')
        +'</div>';
    } else if(d.ingredientes_sin_precio>0){
      costoHtml='<div style="margin-top:8px;padding:8px 12px;background:#fffbeb;border-radius:6px;font-size:0.84em;color:#b7791f;">&#9888; No hay precios de referencia. <a href="#" onclick="abrirPreciosMP();return false;">Configura precios por material</a> para ver costo estimado.</div>';
    }
    panel.innerHTML='<div style="background:'+bg+';border:2px solid '+brd+';border-radius:10px;padding:14px 16px;">'
      +'<strong style="color:'+brd+';font-size:1em;">'+ico+' '+titulo+'</strong>'
      +'<div style="overflow-x:auto;margin-top:10px;"><table class="table" style="font-size:0.85em;margin:0;">'
      +'<thead><tr><th>Material</th><th style="text-align:right;">Requerido</th>'
      +'<th style="text-align:right;">Disponible</th><th style="text-align:right;">Estado</th>'
      +'<th style="text-align:right;">Costo</th></tr></thead>'
      +'<tbody>'+rows+'</tbody></table></div>'
      +costoHtml
      +(d.factible?'<p style="margin:10px 0 0;font-size:0.85em;color:#555;">&#128994; Puedes registrar la produccion con seguridad.</p>'
        :'<p style="margin:10px 0 0;font-size:0.85em;color:#c0392b;">&#9888; Revisa el stock o genera OC de compra antes de producir.</p>')
      +'</div>';
    panel.scrollIntoView({behavior:'smooth'});
  }catch(e){panel.innerHTML='<span style="color:#e74c3c;">Error: '+e.message+'</span>';}
}
async function abrirPreciosMP(){
  /* Abre un modal para editar precios de referencia de MPs */
  var r=await fetch('/api/maestro-mps');
  var d=await r.json();
  var mps=d.mps||[];
  var rows=mps.map(function(m){
    return '<tr><td>'+m.codigo_mp+'</td><td>'+m.nombre_comercial+'</td>'
      +'<td><input type="number" step="0.01" min="0" value="'+(m.precio_referencia||0)+'" id="pr-'+m.codigo_mp+'" style="width:110px;padding:3px 6px;border:1px solid #ccc;border-radius:4px;"></td>'
      +'<td><button onclick="guardarPrecioMP(\\''+m.codigo_mp+'\\')" style="padding:3px 10px;font-size:0.8em;background:#6c5ce7;color:#fff;border:none;border-radius:4px;cursor:pointer;">Guardar</button></td></tr>';
  }).join('');
  var modal=document.createElement('div');
  modal.id='modal-precios-mp';
  modal.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML='<div style="background:#fff;border-radius:12px;padding:24px;max-width:700px;width:95%;max-height:80vh;overflow-y:auto;">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">'
    +'<h3 style="margin:0;">&#128176; Precios de Referencia — Materias Primas</h3>'
    +'<button onclick="document.getElementById(\\'modal-precios-mp\\').remove()" style="background:none;border:none;font-size:1.4em;cursor:pointer;">&#10006;</button></div>'
    +'<p style="font-size:0.85em;color:#718096;margin:0 0 12px;">Precio por kg (usado para estimar costo de fórmulas). Fuente: última OC o manual.</p>'
    +'<div style="overflow-x:auto;"><table class="table" style="font-size:0.85em;">'
    +'<thead><tr><th>Código</th><th>Material</th><th>Precio/kg ($)</th><th></th></tr></thead>'
    +'<tbody>'+rows+'</tbody></table></div></div>';
  document.body.appendChild(modal);
  modal.addEventListener('click',function(e){if(e.target===modal)modal.remove();});
}
async function guardarPrecioMP(codigo){
  var inp=document.getElementById('pr-'+codigo);
  if(!inp)return;
  var precio=parseFloat(inp.value)||0;
  var r=await fetch('/api/maestro-mp/'+codigo+'/precio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({precio_kg:precio,origen:'manual'})});
  var d=await r.json();
  if(d.ok){inp.style.background='#f0fff4';setTimeout(function(){inp.style.background='';},1500);}
  else alert('Error al guardar precio');
}

async function iniciarRegistroProd(){
  var prod=document.getElementById('prod-sel').value||document.getElementById('prod-manual').value;
  var kg=parseFloat(document.getElementById('prod-kg').value);
  if(!prod||!kg||kg<=0){document.getElementById('prod-msg').innerHTML='<span style="color:red;">Completa producto y cantidad</span>';return;}
  // Registrar producción MP
  var obs=document.getElementById('prod-obs').value;
  var pres=document.getElementById('prod-presentacion').value;
  var sku_pt=document.getElementById('prod-sku-pt')?document.getElementById('prod-sku-pt').value.trim():'';
  var uds_pt=document.getElementById('prod-uds-pt')?parseInt(document.getElementById('prod-uds-pt').value)||0:0;
  var precio_pt=document.getElementById('prod-precio-pt')?parseFloat(document.getElementById('prod-precio-pt').value)||0:0;
  var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({producto:prod,cantidad_kg:kg,observaciones:obs,presentacion:pres,operador:OPER_ACTUAL,sku_pt:sku_pt,unidades_pt:uds_pt,precio_pt:precio_pt})});
  var d=await r.json();
  if(!r.ok){document.getElementById('prod-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';return;}
  document.getElementById('prod-msg').innerHTML='<span style="color:green;">&#10003; Produccion registrada: '+d.lote+'</span>';
  _prodPendiente={lote:d.lote};
  // Cargar MEE catalogos y mostrar panel
  var rm=await fetch('/api/mee/stock'); var dm=await rm.json();
  _meeData=dm.items||[];
  renderMEEConsumoRows();
  document.getElementById('mee-consumo-panel').style.display='block';
  document.getElementById('mee-consumo-panel').scrollIntoView({behavior:'smooth'});
}
function renderMEEConsumoRows(){
  var cats=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Otro'];
  var html=cats.map(function(cat){
    var opts=_meeData.filter(function(x){return x.categoria===cat||cat==='Otro';});
    if(cat!=='Otro') opts=_meeData.filter(function(x){return x.categoria===cat;});
    var optsHtml='<option value="__NA__">No aplica</option>'+opts.map(function(x){return '<option value="'+x.codigo+'">'+x.codigo+' — '+x.descripcion+'</option>';}).join('');
    return '<div style="display:grid;grid-template-columns:110px 1fr 140px;gap:10px;align-items:center;margin-bottom:10px;padding:10px;background:white;border-radius:8px;border:1px solid #e0e0e0;">'
      +'<span style="font-size:0.85em;font-weight:700;color:#4A6741;">'+cat+'</span>'
      +'<select id="mee-cons-'+cat+'" onchange="toggleMEECant(&quot;'+cat+'&quot;)" style="width:100%;font-size:0.85em;">'+optsHtml+'</select>'
      +'<input type="number" id="mee-cant-'+cat+'" placeholder="Cantidad (und)" min="0" style="font-size:0.85em;display:none;">'
      +'</div>';
  }).join('');
  document.getElementById('mee-rows-container').innerHTML=html;
}
function toggleMEECant(cat){
  var sel=document.getElementById('mee-cons-'+cat).value;
  document.getElementById('mee-cant-'+cat).style.display=sel==='__NA__'?'none':'block';
  if(sel!=='__NA__') document.getElementById('mee-cant-'+cat).focus();
}
async function confirmarProdCompleta(){
  if(!_prodPendiente){alert('No hay produccion pendiente');return;}
  var cats=['Envase','Tapa','Etiqueta','Plegable','Serigrafia','Gotero','Otro'];
  var consumos=[];
  for(var i=0;i<cats.length;i++){
    var cat=cats[i];
    var sel=document.getElementById('mee-cons-'+cat);
    if(!sel)continue;
    var cod=sel.value;
    if(cod==='__NA__')continue;
    var cant=parseFloat(document.getElementById('mee-cant-'+cat).value)||0;
    if(cod&&cant>0)consumos.push({codigo_mee:cod,cantidad:cant,referencia:_prodPendiente.lote});
  }
  if(consumos.length>0){
    var r=await fetch('/api/movimientos-mee/lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({movimientos:consumos,operador:OPER_ACTUAL,referencia:_prodPendiente.lote})});
    var d=await r.json();
    if(!r.ok){document.getElementById('mee-consumo-msg').innerHTML='<span style="color:red;">Error al registrar MEE: '+(d.error||'')+'</span>';return;}
  }
  document.getElementById('mee-consumo-panel').style.display='none';
  document.getElementById('mee-consumo-msg').innerHTML='';
  _prodPendiente=null;
  var nm=consumos.length;
  document.getElementById('prod-msg').innerHTML='<span style="color:green;font-size:1em;">&#10003; Produccion completa: '+nm+' tipo(s) de MEE descontados.</span>';
  cargarHistProd(); loadMEE();
}
function cancelarMEEConsumoProd(){
  document.getElementById('mee-consumo-panel').style.display='none';
  _prodPendiente=null;
}


window.onload=function(){/* Data loads after operator confirms name */};
function mostrarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel){ panel.style.display='block'; panel.scrollIntoView({behavior:'smooth',block:'nearest'}); }
}
function ocultarFormNuevaMP(){
  var panel=document.getElementById('ing-nueva-mp');
  if(panel) panel.style.display='none';
  ['nmp-cod','nmp-inci','nmp-nombre','nmp-tipo','nmp-prov'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.value='';
  });
  var ns=document.getElementById('nmp-smin'); if(ns) ns.value='500';
  var nm=document.getElementById('nmp-msg'); if(nm) nm.innerHTML='';
}
async function crearNuevaMP(){
  var cod=(document.getElementById('nmp-cod').value||'').toUpperCase().trim();
  var inci=(document.getElementById('nmp-inci').value||'').trim();
  var nombre=(document.getElementById('nmp-nombre').value||'').trim();
  if(!cod||!nombre){alert('Codigo y Nombre Comercial son obligatorios');return;}
  var data={codigo_mp:cod,nombre_inci:inci,nombre_comercial:nombre,
    tipo:(document.getElementById('nmp-tipo').value||'').trim(),
    proveedor:(document.getElementById('nmp-prov').value||'').trim(),
    stock_minimo:parseFloat(document.getElementById('nmp-smin').value)||500};
  try{
    var r=await fetch('/api/maestro-mps',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      document.getElementById('nmp-msg').innerHTML='<div class="alert-success">MP '+cod+' creada en catalogo. Ya puedes usarla en el ingreso.</div>';
      _cat[cod]=data;  // Agregar al catalogo local
      // Pre-llenar el formulario de ingreso
      var f={'ing-cod':cod,'ing-inci':inci,'ing-nombre':nombre,'ing-tipo':data.tipo,'ing-prov':data.proveedor};
      Object.keys(f).forEach(function(id){var el=document.getElementById(id);if(el)el.value=f[id];});
      var st=document.getElementById('ing-status'); if(st){st.textContent='Nueva MP creada y lista para ingresar';st.style.color='#28a745';}
    } else {
      document.getElementById('nmp-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al crear')+'</div>';
    }
  }catch(e){document.getElementById('nmp-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

// ── Funciones CC / Trazabilidad / Conteo Ciclico ──
async function cargarCuarentena(){
  try{
    var r=await fetch('/api/lotes/cuarentena');
    var data=await r.json();
    var tb=document.getElementById('cuar-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:#999;padding:20px;">Sin lotes pendientes de revision QC</td></tr>';return;}
    var h='';
    data.forEach(function(l){
      var esAdmin=(['sebastian','alejandro','hernando'].includes((OPER_ACTUAL||'').toLowerCase()));
      var estadoColor=l.estado_lote==='CUARENTENA'?'#e67e22':l.estado_lote==='CUARENTENA_EXTENDIDA'?'#c0392b':'#888';
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.85em;">'+l.codigo_mp+'</td>';
      h+='<td style="font-size:0.8em;color:#555;">'+(l.nombre_inci||'')+'</td>';
      h+='<td>'+l.nombre+'</td>';
      h+='<td style="font-family:monospace;font-weight:600;">'+l.lote+'</td>';
      h+='<td style="text-align:right;font-weight:600;">'+l.cantidad.toLocaleString()+'</td>';
      h+='<td style="font-size:0.85em;">'+(l.proveedor||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+(l.numero_oc||'')+'</td>';
      h+='<td style="font-size:0.82em;">'+l.fecha.substring(0,10)+'</td>';
      h+='<td><span style="background:'+estadoColor+'20;color:'+estadoColor+';padding:2px 8px;border-radius:10px;font-size:0.8em;font-weight:700;">'+l.estado_lote.replace('_',' ')+'</span></td>';
      h+='<td>';
      if(esAdmin){
        h+='<button onclick="abrirCCModal(JSON.parse(this.dataset.lote))" data-lote="'+JSON.stringify(l).replace(/"/g,'&quot;')+'" style="padding:5px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:0.82em;font-weight:600;">Revisar CC</button>';
      }else{
        h+='<span style="color:#999;font-size:0.82em;">Solo CC/Admin</span>';
      }
      h+='</td></tr>';
    });
    tb.innerHTML=h;
  }catch(e){console.error(e);}
}

function abrirCCModal(lote){
  _ccLoteActual=lote;
  document.getElementById('cc-modal-lote').textContent=lote.lote+' -- '+lote.nombre;
  document.getElementById('cc-firmante').textContent=OPER_ACTUAL;
  document.getElementById('cc-lote-info').innerHTML=
    '<div><b>Codigo:</b> '+lote.codigo_mp+'</div>'+
    '<div><b>INCI:</b> '+(lote.nombre_inci||'--')+'</div>'+
    '<div><b>Cantidad:</b> '+Number(lote.cantidad).toLocaleString()+' g</div>'+
    '<div><b>Proveedor:</b> '+(lote.proveedor||'--')+'</div>'+
    '<div><b>Factura:</b> '+(lote.numero_factura||'--')+'</div>'+
    '<div><b>OC:</b> '+(lote.numero_oc||'--')+'</div>';
  ['cc-coa-ok','cc-lote-coincide','cc-coa-vigente','cc-ficha-ok','cc-muestra-ret'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  ['cc-solub-ok','cc-solub-fail','cc-aql-ok','cc-aql-fail','cc-aql-ext'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.checked=false;
  });
  document.getElementById('cc-aql-obs').value='';
  document.getElementById('cc-obs-final').value='';
  document.getElementById('cc-modal-msg').innerHTML='';
  document.getElementById('cc-modal').style.display='flex';
}

function cerrarCCModal(){
  document.getElementById('cc-modal').style.display='none';
  _ccLoteActual=null;
}

async function enviarRevisionCC(){
  if(!_ccLoteActual){return;}
  var coaOk=document.getElementById('cc-coa-ok').checked;
  var loteCoincide=document.getElementById('cc-lote-coincide').checked;
  var coaVigente=document.getElementById('cc-coa-vigente').checked;
  var fichaOk=document.getElementById('cc-ficha-ok').checked;
  var solubResult=document.querySelector('input[name="cc-solub"]:checked');
  var aqlResult=document.querySelector('input[name="cc-aql"]:checked');
  var aqlObs=document.getElementById('cc-aql-obs').value.trim();
  var muestraRet=document.getElementById('cc-muestra-ret').checked;
  var obsFinal=document.getElementById('cc-obs-final').value.trim();
  var msg=document.getElementById('cc-modal-msg');
  if(!solubResult){msg.innerHTML='<div class="alert-error">Selecciona resultado de solubilidad</div>';return;}
  if(!aqlResult){msg.innerHTML='<div class="alert-error">Selecciona resultado AQL</div>';return;}
  if((aqlResult.value==='NO_CONFORME'||aqlResult.value==='CUARENTENA_EXTENDIDA')&&!aqlObs){
    msg.innerHTML='<div class="alert-error">Las observaciones son obligatorias para este resultado</div>';return;
  }
  var payload={
    mov_id:_ccLoteActual.id,
    lote:_ccLoteActual.lote,
    codigo_mp:_ccLoteActual.codigo_mp,
    coa_ok:coaOk,
    lote_coincide:loteCoincide,
    coa_vigente:coaVigente,
    ficha_ok:fichaOk,
    solubilidad:solubResult.value,
    resultado_aql:aqlResult.value,
    observaciones_aql:aqlObs,
    muestra_retencion:muestraRet,
    observaciones:obsFinal,
    firmante:OPER_ACTUAL
  };
  try{
    document.getElementById('cc-submit-btn').disabled=true;
    document.getElementById('cc-submit-btn').textContent='Registrando...';
    var r=await fetch('/api/lotes/cc-review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var res=await r.json();
    if(r.ok){
      msg.innerHTML='<div class="alert-success">'+res.message+'</div>';
      document.getElementById('cuar-msg').innerHTML='<div class="alert-success">Revision CC registrada -- '+res.estado+' -- Lote: '+payload.lote+'</div>';
      setTimeout(function(){cerrarCCModal();cargarCuarentena();},1800);
    }else{
      msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
    }
  }catch(e){
    msg.innerHTML='<div class="alert-error">Error: '+e.message+'</div>';
  }finally{
    document.getElementById('cc-submit-btn').disabled=false;
    document.getElementById('cc-submit-btn').textContent='Firmar y Registrar';
  }
}

async function buscarTrazabilidad(){
  var lote=(document.getElementById('trz-lote').value||'').trim();
  if(!lote){alert('Ingresa un numero de lote');return;}
  try{
    var r=await fetch('/api/trazabilidad/'+encodeURIComponent(lote));
    var data=await r.json();
    if(!data.ingreso){
      document.getElementById('trz-msg').innerHTML='<div class="alert-error">Lote no encontrado: '+lote+'</div>';
      document.getElementById('trz-result-lote').style.display='none';
      return;
    }
    document.getElementById('trz-msg').innerHTML='';
    document.getElementById('trz-result-lote').style.display='block';
    var ing=data.ingreso;
    document.getElementById('trz-ingreso').innerHTML=
      '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;">'+
      '<div><b>Codigo:</b> '+ing.codigo_mp+'</div>'+
      '<div><b>Nombre:</b> '+ing.nombre+'</div>'+
      '<div><b>INCI:</b> '+(ing.nombre_inci||'—')+'</div>'+
      '<div><b>Cantidad:</b> '+Number(ing.cantidad_g).toLocaleString()+' g</div>'+
      '<div><b>Proveedor:</b> '+(ing.proveedor||'—')+'</div>'+
      '<div><b>Factura:</b> '+(ing.factura||'—')+'</div>'+
      '<div><b>OC:</b> '+(ing.orden_compra||'—')+'</div>'+
      '<div><b>Precio/kg:</b> '+(ing.precio_kg?'$'+Number(ing.precio_kg).toLocaleString('es-CO'):'—')+'</div>'+
      '<div><b>Fecha:</b> '+(ing.fecha?ing.fecha.substring(0,10):'—')+'</div>'+
      '</div>';
    document.getElementById('trz-nprod').textContent=data.total_producciones;
    var tb=document.getElementById('trz-prod-tbody');
    if(!data.producciones.length){
      tb.innerHTML='<tr><td colspan="4" style="text-align:center;color:#999;">Este lote no ha sido usado en produccion</td></tr>';
    } else {
      var h='';
      data.producciones.forEach(function(p){
        h+='<tr><td>'+p.producto+'</td><td>'+p.fecha.substring(0,10)+'</td><td>'+p.operador+'</td><td style="text-align:right;">'+Number(p.cantidad_g).toLocaleString()+'</td></tr>';
      });
      tb.innerHTML=h;
    }
  }catch(e){document.getElementById('trz-msg').innerHTML='<div class="alert-error">Error: '+e.message+'</div>';}
}

async function buscarTrazabilidadPT(){
  var lote=(document.getElementById('trz-lote-pt')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote PT (ej: PROD-00001)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-pt/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+d.error+'</div>';return;}
    var html='<div style="background:#f8f9ff;border:1px solid #c3cfe2;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#6c5ce7;">&#128203; Lote PT: '+d.lote_ref+'</h4>';
    if(d.produccion){
      var p=d.produccion;
      html+='<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;font-size:0.88em;margin-bottom:12px;">';
      html+='<div><b>Producto:</b> '+(p.producto||'&#8212;')+'</div>';
      html+='<div><b>Cantidad:</b> '+(p.cantidad_kg?Number(p.cantidad_kg).toFixed(2)+' kg':'&#8212;')+'</div>';
      html+='<div><b>Fecha:</b> '+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</div>';
      html+='<div><b>Operador:</b> '+(p.operador||'&#8212;')+'</div>';
      html+='</div>';
    }
    var mps=d.mps_consumidas||[];
    html+='<h5 style="margin:0 0 8px;color:#2B7A78;">Materias Primas Consumidas ('+mps.length+')</h5>';
    if(mps.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;">';
      html+='<thead><tr style="background:#f0f0f0;"><th style="padding:4px 8px;text-align:left;">Lote MP</th><th style="padding:4px 8px;text-align:left;">Material</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th><th style="padding:4px 8px;text-align:left;">Proveedor</th><th style="padding:4px 8px;text-align:left;">Vence</th></tr></thead><tbody>';
      var det=d.detalle_lotes_mp||{};
      mps.forEach(function(m){
        var info=det[m.lote]||{};
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+m.lote+'</td><td style="padding:4px 8px;">'+(m.material||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(m.cantidad_g||0).toLocaleString()+'</td><td style="padding:4px 8px;">'+(info.proveedor||'&#8212;')+'</td><td style="padding:4px 8px;">'+(info.vencimiento?info.vencimiento.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron lotes MP asociados (la produccion puede no tener lote asignado aun).</p>';
    }
    var desp=d.despachos||[];
    if(desp.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Despachos a Clientes ('+desp.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:right;">Cantidad</th><th style="padding:4px 8px;text-align:left;">Remision</th></tr></thead><tbody>';
      desp.forEach(function(ds){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(ds.fecha?ds.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.cliente||'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+(ds.cantidad||'&#8212;')+'</td><td style="padding:4px 8px;">'+(ds.remision||'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
}

async function buscarTrazabilidadMP(){
  var lote=(document.getElementById('trz-lote-mp')||{}).value||'';
  lote=lote.trim();
  if(!lote){alert('Ingresa un numero de lote MP (ej: ESP240115MP1)');return;}
  var div=document.getElementById('trz-result');
  if(!div)return;
  div.innerHTML='<p style="color:#888;font-size:0.9em;">Buscando...</p>';
  try{
    var r=await fetch('/api/trazabilidad/lote-mp/'+encodeURIComponent(lote));
    var d=await r.json();
    if(d.error){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">'+d.error+'</div>';return;}
    var html='<div style="background:#f8fff8;border:1px solid #c3e2cf;border-radius:10px;padding:16px;margin-bottom:12px;">';
    html+='<h4 style="margin:0 0 10px;color:#00b894;">&#128203; Lote MP: '+d.lote_mp+'</h4>';
    if(d.material){
      var mat=d.material;
      html+='<div style="font-size:0.88em;margin-bottom:12px;"><b>Material:</b> '+(mat.nombre||d.lote_mp)+' <span style="color:#888;">('+d.lote_mp+')</span>';
      if(mat.proveedor) html+=' | <b>Proveedor:</b> '+mat.proveedor;
      if(mat.fecha_ingreso) html+=' | <b>Ingreso:</b> '+mat.fecha_ingreso.substring(0,10);
      html+='</div>';
    }
    var prods=d.producciones||[];
    html+='<h5 style="margin:0 0 8px;color:#6c5ce7;">Producciones donde se uso ('+prods.length+')</h5>';
    if(prods.length){
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#f0f0f8;"><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th><th style="padding:4px 8px;text-align:right;">Cant (g)</th></tr></thead><tbody>';
      prods.forEach(function(p){
        html+='<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(p.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(p.fecha?p.fecha.substring(0,10):'&#8212;')+'</td><td style="padding:4px 8px;text-align:right;">'+Number(p.cantidad_g||0).toLocaleString()+'</td></tr>';
      });
      html+='</tbody></table>';
    } else {
      html+='<p style="color:#999;font-size:0.85em;">No se encontraron producciones para este lote.</p>';
    }
    var clientes=d.clientes_afectados||[];
    if(clientes.length){
      html+='<h5 style="margin:12px 0 8px;color:#e17055;">Clientes que recibieron este material ('+clientes.length+')</h5>';
      html+='<table style="width:100%;font-size:0.82em;border-collapse:collapse;"><thead><tr style="background:#fff3f0;"><th style="padding:4px 8px;text-align:left;">Cliente</th><th style="padding:4px 8px;text-align:left;">Lote PT</th><th style="padding:4px 8px;text-align:left;">Producto</th><th style="padding:4px 8px;text-align:left;">Fecha</th></tr></thead><tbody>';
      clientes.forEach(function(cl){
        html+='<tr style="border-bottom:1px solid #fee;"><td style="padding:4px 8px;">'+(cl.cliente||'&#8212;')+'</td><td style="padding:4px 8px;font-family:monospace;font-size:0.9em;">'+(cl.lote_ref||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.producto||'&#8212;')+'</td><td style="padding:4px 8px;">'+(cl.fecha?cl.fecha.substring(0,10):'&#8212;')+'</td></tr>';
      });
      html+='</tbody></table>';
    }
    html+='</div>';
    div.innerHTML=html;
  }catch(e){div.innerHTML='<div style="color:#e74c3c;padding:12px;background:#ffeaea;border-radius:8px;">Error: '+e.message+'</div>';}
}

var _conteoActivo = null;
var _conteoItems = [];

async function cargarEstanterias(){
  try{
    var r = await fetch('/api/conteo/estanterias');
    var data = await r.json();
    var sel = document.getElementById('cnt-est-sel');
    if(!sel) return;
    while(sel.options.length > 1) sel.remove(1);
    data.forEach(function(e){
      var opt = document.createElement('option');
      opt.value = e.estanteria;
      opt.textContent = e.estanteria + ' (' + e.total_mps + ' MPs, ' + (e.stock_total/1000).toFixed(1) + ' kg)';
      sel.appendChild(opt);
    });
  }catch(e){}
}

async function cargarProgramacionCiclica(){
  try{
    var r = await fetch('/api/conteo/programacion');
    var d = await r.json();
    var tbody = document.getElementById('cnt-prog-rows');
    if(!tbody) return;
    if(!d.semanas || d.semanas.length === 0){
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:14px;color:#999;">Sin datos de estanterias</td></tr>';
      return;
    }
    var html = '';
    d.semanas.forEach(function(s){
      var bg = s.es_actual ? 'background:linear-gradient(135deg,#d4f7f2,#e8faf7);font-weight:700;' : '';
      var badge = '';
      if(s.conteo_estado === 'Abierto') badge = '<span style="background:#fff3cd;color:#856404;padding:2px 8px;border-radius:10px;font-size:0.82em;">En Curso</span>';
      else if(s.conteo_estado === 'Cerrado') badge = '<span style="background:#d1f2d1;color:#1a6b1a;padding:2px 8px;border-radius:10px;font-size:0.82em;">Completado</span>';
      else badge = '<span style="background:#f0f0f0;color:#666;padding:2px 8px;border-radius:10px;font-size:0.82em;">Pendiente</span>';
      var semLabel = s.es_actual ? 'Sem. '+s.semana+' (Esta semana)' : 'Sem. '+s.semana;
      var accion = '';
      if(s.es_actual && s.conteo_estado !== 'Cerrado'){
        accion = `<button onclick="iniciarConteoProgramado('${s.estanteria}')" style="padding:4px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;font-size:0.82em;cursor:pointer;">${s.conteo_estado==='Abierto'?'Retomar':'Iniciar'}</button>`;
      }
      html += '<tr style="border-bottom:1px solid #e0ece9;'+bg+'">'
            + '<td style="padding:7px 12px;">'+semLabel+'</td>'
            + '<td style="padding:7px 12px;">'+s.lunes+'</td>'
            + '<td style="padding:7px 12px;font-weight:600;">'+s.estanteria+'</td>'
            + '<td style="padding:7px 12px;text-align:center;">'+badge+'</td>'
            + '<td style="padding:7px 12px;text-align:center;">'+accion+'</td>'
            + '</tr>';
    });
    html += '<tr style="background:#f5f5f5;font-size:0.8em;color:#888;"><td colspan="5" style="padding:6px 12px;">Total estanterias en rotacion: '+d.total_estanterias+' — ciclo completo cada '+d.total_estanterias+' semanas</td></tr>';
    tbody.innerHTML = html;
  }catch(e){
    var tbody = document.getElementById('cnt-prog-rows');
    if(tbody) tbody.innerHTML = '<tr><td colspan="5" style="color:#c00;padding:10px;">Error cargando programacion</td></tr>';
  }
}

function iniciarConteoProgramado(estanteria){
  var sel = document.getElementById('cnt-est-sel');
  if(sel){
    for(var i=0; i<sel.options.length; i++){
      if(sel.options[i].value === estanteria){ sel.selectedIndex = i; break; }
    }
  }
  iniciarConteo();
}

async function iniciarConteo(){
  var est = document.getElementById('cnt-est-sel').value;
  var resp = document.getElementById('cnt-responsable').value.trim() || OPER_ACTUAL;
  if(!est){alert('Selecciona una estanteria'); return;}
  try{
    var r = await fetch('/api/conteo/iniciar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({estanteria:est,responsable:resp})});
    var res = await r.json();
    if(!r.ok){alert(res.error||'Error'); return;}
    _conteoActivo = {id: res.conteo_id, numero: res.numero, estanteria: est};
    if(res.resuming){
      document.getElementById('cnt-msg').innerHTML = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:8px 12px;color:#856404;font-size:0.88em;">&#9888; Retomando conteo abierto existente: '+res.numero+'</div>';
    }
    document.getElementById('cnt-numero').textContent = res.numero;
    document.getElementById('cnt-est-label').textContent = est;
    document.getElementById('cnt-panel').style.display = 'block';
    await cargarItemsConteo(est);
  }catch(e){alert('Error: '+e.message);}
}

async function cargarItemsConteo(est){
  try{
    var r = await fetch('/api/conteo/materiales?estanteria='+encodeURIComponent(est));
    _conteoItems = await r.json();
    var causas = ['Error de conteo','Consumo no descargado','Ingreso no registrado','Error unidad de medida','Merma justificada','Traslado no registrado','Material no identificado','Otro'];
    var causaOpts = causas.map(function(c){return '<option>'+c+'</option>';}).join('');
    var h = '';
    _conteoItems.forEach(function(mp, i){
      h += '<tr id="cnt-row-'+i+'">';
      h += '<td style="font-family:monospace;font-size:0.82em;">'+mp.codigo_mp+'</td>';
      h += '<td style="font-size:0.78em;color:#555;">'+(mp.inci||'')+'</td>';
      h += '<td style="font-size:0.88em;">'+mp.nombre+'</td>';
      h += '<td style="text-align:right;font-weight:600;font-family:monospace;">'+Number(mp.stock_sistema).toLocaleString()+'</td>';
      h += '<td><input type="number" id="cnt-fis-'+i+'" min="0" step="0.1" oninput="calcDiff('+i+','+mp.stock_sistema+','+mp.precio_ref+')" style="width:120px;padding:6px;border:1px solid #dde;border-radius:6px;text-align:right;font-family:monospace;"></td>';
      h += '<td id="cnt-diff-'+i+'" style="text-align:right;font-family:monospace;font-weight:700;">--</td>';
      h += '<td id="cnt-pct-'+i+'" style="font-size:0.85em;">--</td>';
      h += '<td id="cnt-val-'+i+'" style="font-size:0.82em;color:#888;">--</td>';
      h += '<td><select id="cnt-causa-'+i+'" style="width:150px;padding:5px;border:1px solid #dde;border-radius:6px;font-size:0.8em;"><option value="">Sin diferencia</option>'+causaOpts+'</select></td>';
      h += '<td id="cnt-adj-'+i+'"></td>';
      h += '</tr>';
    });
    document.getElementById('cnt-tbody').innerHTML = h || '<tr><td colspan="10" style="text-align:center;color:#999;">Sin materiales en esta estanteria</td></tr>';
  }catch(e){console.error(e);}
}

function calcDiff(i, stockSis, precioRef){
  var fis = parseFloat(document.getElementById('cnt-fis-'+i).value);
  var diffEl = document.getElementById('cnt-diff-'+i);
  var pctEl = document.getElementById('cnt-pct-'+i);
  var valEl = document.getElementById('cnt-val-'+i);
  var row = document.getElementById('cnt-row-'+i);
  if(isNaN(fis)){diffEl.textContent='--';pctEl.textContent='--';valEl.textContent='--';return;}
  var diff = fis - stockSis;
  var pct = stockSis > 0 ? Math.abs(diff/stockSis)*100 : 0;
  var valDiff = Math.abs(diff/1000) * precioRef;
  diffEl.textContent = (diff >= 0 ? '+' : '') + diff.toLocaleString('es-CO',{maximumFractionDigits:1});
  diffEl.style.color = diff === 0 ? '#27ae60' : diff > 0 ? '#2980b9' : '#e74c3c';
  pctEl.textContent = pct.toFixed(1) + '%';
  if(pct > 5){
    pctEl.style.color = '#e74c3c';
    pctEl.textContent += ' ⚠ GERENCIA';
    row.style.background = '#fff5f5';
  } else {
    pctEl.style.color = pct > 2 ? '#e67e22' : '#27ae60';
    row.style.background = '';
  }
  valEl.textContent = valDiff > 0 ? '$'+valDiff.toLocaleString('es-CO',{maximumFractionDigits:0}) : '--';
}

async function guardarConteo(){
  if(!_conteoActivo){alert('Inicia un conteo primero'); return;}
  var items = [];
  _conteoItems.forEach(function(mp, i){
    var fisEl = document.getElementById('cnt-fis-'+i);
    if(!fisEl || fisEl.value === '') return;
    items.push({
      codigo_mp: mp.codigo_mp,
      nombre: mp.nombre,
      stock_sistema: mp.stock_sistema,
      stock_fisico: parseFloat(fisEl.value),
      precio_ref: mp.precio_ref,
      estanteria: mp.estanteria,
      causa_diferencia: document.getElementById('cnt-causa-'+i).value
    });
  });
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/guardar',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({items:items})});
    var res = await r.json();
    if(r.ok){
      var msg = 'Guardado. ';
      if(res.items_con_diferencia > 0) msg += res.items_con_diferencia+' item(s) con diferencias.';
      document.getElementById('cnt-resumen').style.display = 'block';
      document.getElementById('cnt-resumen').innerHTML = msg + ' Revisa los items marcados con ⚠ GERENCIA antes de cerrar.';
      await cargarHistorialConteos();
    }
  }catch(e){alert('Error: '+e.message);}
}

async function cerrarConteo(){
  if(!_conteoActivo) return;
  if(!confirm('Cerrar el conteo? Ya no se podran editar los conteos fisicos.')) return;
  try{
    var r = await fetch('/api/conteo/'+_conteoActivo.id+'/cerrar',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var res = await r.json();
    document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    document.getElementById('cnt-panel').style.display = 'none';
    _conteoActivo = null;
    await cargarHistorialConteos();
    await cargarEstanterias();
  }catch(e){alert('Error: '+e.message);}
}

async function aplicarAjuste(itemId){
  if(!confirm('Aplicar ajuste de inventario? Se registrara un movimiento de correccion en el sistema.')) return;
  try{
    var r = await fetch('/api/conteo/0/ajustar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({item_id:itemId})});
    var res = await r.json();
    if(r.ok){
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-success">'+res.message+'</div>';
    }else{
      document.getElementById('cnt-msg').innerHTML = '<div class="alert-error">'+(res.error||'Error')+'</div>';
    }
  }catch(e){}
}

async function cargarHistorialConteos(){
  try{
    var r = await fetch('/api/conteo/historial');
    var data = await r.json();
    var tb = document.getElementById('cnt-hist-tbody');
    if(!data.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin conteos</td></tr>';return;}
    var h = '';
    data.forEach(function(c){
      var estadoColor = c.estado === 'Cerrado' ? '#27ae60' : '#e67e22';
      h += '<tr>';
      h += '<td style="font-family:monospace;font-size:0.85em;">'+c.numero+'</td>';
      h += '<td>'+(c.estanteria||'')+'</td>';
      h += '<td style="font-size:0.82em;">'+(c.fecha_inicio?c.fecha_inicio.substring(0,10):'')+'</td>';
      h += '<td>'+(c.responsable||'')+'</td>';
      h += '<td><span style="color:'+estadoColor+';font-weight:700;">'+c.estado+'</span></td>';
      h += '<td style="text-align:center;">'+c.total_items+'</td>';
      h += '<td style="text-align:center;color:'+(c.items_diferencia>0?'#e74c3c':'#27ae60')+';">'+c.items_diferencia+'</td>';
      h += '<td style="text-align:center;">';
      if(c.items_gerencia > 0) h += '<span style="color:#e74c3c;font-weight:700;">'+c.items_gerencia+' ⚠</span>';
      else h += '<span style="color:#27ae60;">OK</span>';
      h += '</td></tr>';
    });
    tb.innerHTML = h;
  }catch(e){}
}

async function cargarMeeAlertas(){
  try{
    var r=await fetch('/api/mee/alertas'); var d=await r.json(); var res=d.resumen||{};
    var cT=document.getElementById('mee-c-total'); var cB=document.getElementById('mee-c-bajo');
    var cS=document.getElementById('mee-c-semana'); var cM=document.getElementById('mee-c-mes');
    if(cT) cT.textContent=res.total_mee||0;
    if(cB){ cB.textContent=res.bajo_minimo||0; var card=document.getElementById('mee-card-bajo'); if(card) card.style.background=(res.bajo_minimo>0)?'#e74c3c':'#27ae60'; }
    if(cS) cS.textContent=res.movimientos_semana||0;
    if(cM) cM.textContent=res.entradas_mes||0;
    var panel=document.getElementById('mee-alertas-panel'); if(!panel) return;
    if(d.bajo_minimo&&d.bajo_minimo.length>0){
      var h='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:10px;padding:14px;margin-bottom:10px;"><strong style="color:#856404;">&#9888; '+d.bajo_minimo.length+' materiales bajo stock minimo</strong><div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:8px;">';
      d.bajo_minimo.forEach(function(m){ var pct=Math.round(m.ratio*100); var col=pct<=0?'#e74c3c':'#e67e22'; h+='<div style="background:white;border:1px solid #ffc107;border-radius:6px;padding:6px 12px;font-size:0.85em;"><span style="font-weight:700;color:'+col+';">'+m.descripcion+'</span> <span style="color:#888;">['+m.categoria+'] </span><span style="color:'+col+';">'+m.stock_actual+'/'+m.stock_minimo+' '+m.unidad+' ('+pct+'%)</span></div>'; });
      h+='</div></div>';
      if(d.obsolescencia&&d.obsolescencia.length>0){ h+='<div style="background:#fff;border:1px solid #dee2e6;border-radius:8px;padding:10px 14px;font-size:0.85em;color:#6c757d;margin-bottom:8px;"><strong>&#128337; Sin movimiento +90 dias:</strong> '+d.obsolescencia.map(function(o){return o.descripcion+' ('+o.stock_actual+')';}).join(' · ')+'</div>'; }
      panel.innerHTML=h;
    } else { panel.innerHTML='<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:8px;padding:10px 14px;color:#155724;margin-bottom:10px;">&#10003; Todos los MEE sobre stock minimo</div>'; }
  }catch(e){}
}
async function cargarMeeStock(){
  var cat = '';
  var sel = document.getElementById('mee-cat-filter-bodega') || document.getElementById('mee-cat-filter');
  if(sel) cat = sel.value || '';
  try{
    var r = await fetch('/api/mee/stock?categoria='+encodeURIComponent(cat));
    var d = await r.json();
    if(sel && d.categorias){
      var cur = sel.value;
      sel.innerHTML = '<option value="">Todas ('+d.total+')</option>';
      d.categorias.forEach(function(c){ sel.innerHTML += '<option value="'+c+'"'+(c===cur?' selected':'')+'>'+c+'</option>'; });
    }
    var codSel = document.getElementById('mee-codigo-sel');
    if(codSel && d.items){
      var cur2 = codSel.value;
      codSel.innerHTML = '<option value="">-- Seleccionar material --</option>';
      d.items.forEach(function(m){
        codSel.innerHTML += '<option value="'+m.codigo+'" data-stock="'+m.stock_actual+'" data-unidad="'+m.unidad+'" data-min="'+m.stock_minimo+'">'+m.codigo+' — '+m.descripcion+'</option>';
      });
      if(cur2) codSel.value = cur2;
    }
    var tb = document.getElementById('mee-stock-tbody');
    if(!tb) return;
    if(!d.items || !d.items.length){
      tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin items activos</td></tr>'; return;
    }
    var aC={critico:'#e74c3c',bajo:'#e67e22',advertencia:'#f39c12',ok:'#27ae60',sin_minimo:'#95a5a6'};
    var aL={critico:'&#9940; Critico',bajo:'&#9888; Bajo',advertencia:'&#128993; Alerta',ok:'&#10003; OK',sin_minimo:'—'};
    var hoy=new Date(); hoy.setHours(0,0,0,0);
    var h='';
    d.items.forEach(function(m){
      var c=aC[m.alerta]||'#95a5a6';
      var lbl=aL[m.alerta]||'';
      var lastMov=(m.ultima_entrada||m.ultima_salida||'').substring(0,10);
      var ob=m.obsoleto?' <span style="background:#ffc107;color:#856404;border-radius:3px;padding:1px 5px;font-size:0.75em;">+90d</span>':'';
      var rot='<span style="color:#bbb;font-size:0.8em;">Sin salidas</span>';
      if(m.ultima_salida){
        var ds=Math.floor((hoy-new Date(m.ultima_salida.substring(0,10)))/864e5);
        var rc=ds<=30?'#27ae60':ds<=90?'#f39c12':'#e74c3c';
        var rl=ds<=30?'Rapida ('+ds+'d)':ds<=90?'Media ('+ds+'d)':'Lenta ('+ds+'d)';
        rot='<span style="color:'+rc+';font-size:0.8em;font-weight:600;">'+rl+'</span>';
      }
      h+='<tr>';
      h+='<td style="font-family:monospace;font-size:0.82em;color:#555;">'+m.codigo+'</td>';
      h+='<td style="font-size:0.88em;">'+m.descripcion+ob+'</td>';
      h+='<td style="font-size:0.8em;color:#777;">'+m.categoria+'</td>';
      h+='<td style="font-weight:700;">'+m.stock_actual+' <span style="color:#999;font-size:0.8em;">'+m.unidad+'</span></td>';
      h+='<td style="color:#aaa;font-size:0.88em;">'+(m.stock_minimo||'—')+'</td>';
      h+='<td><span style="color:'+c+';font-weight:600;font-size:0.82em;">'+lbl+'</span></td>';
      h+='<td style="font-size:0.8em;color:#999;">'+(lastMov||'<span style="color:#ddd;">Ninguno</span>')+'</td>';
      h+='<td>'+rot+'</td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
  }catch(e){}
}
function meeActualizarTipo(tipo){ var iS=tipo==='Salida'; var lg=document.getElementById('mee-lote-group'); var bg=document.getElementById('mee-batch-group'); if(lg) lg.style.display=iS?'none':'block'; if(bg) bg.style.display=iS?'block':'none'; }
function meeSelChange(){ var sel=document.getElementById('mee-codigo-sel'); var prev=document.getElementById('mee-stock-preview'); var und=document.getElementById('mee-unidad'); if(!sel||!sel.value){if(prev)prev.style.display='none';return;} var opt=sel.options[sel.selectedIndex]; var st=opt.getAttribute('data-stock'); var u=opt.getAttribute('data-unidad')||'und'; var mn=opt.getAttribute('data-min'); if(prev){var r=mn>0?(st/mn*100).toFixed(0):null; var col=!r?'#666':(r<100?'#e74c3c':'#27ae60'); prev.style.display='block'; prev.innerHTML='&#128230; Stock: <strong style="color:'+col+';">'+st+' '+u+'</strong> | Minimo: <strong>'+mn+' '+u+'</strong>'+(r?' ('+r+'%)':'');} if(und) und.value=u; }
async function registrarMeeMovimiento(){ var tipo=(document.getElementById('mee-tipo')||{}).value; var codigo=(document.getElementById('mee-codigo-sel')||{}).value; var cantidad=parseFloat((document.getElementById('mee-cantidad')||{}).value); var unidad=(document.getElementById('mee-unidad')||{}).value||'und'; var lote=(document.getElementById('mee-lote')||{}).value||''; var batch=(document.getElementById('mee-batch')||{}).value||''; var obs=(document.getElementById('mee-obs')||{}).value||''; var msg=document.getElementById('mee-form-msg');
  if(!codigo){if(msg)msg.innerHTML='<div class="alert-error">Selecciona un material MEE</div>';return;}
  if(!cantidad||cantidad<=0){if(msg)msg.innerHTML='<div class="alert-error">Ingresa una cantidad valida</div>';return;}
  try{ var r=await fetch('/api/mee/movimiento',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipo:tipo,codigo:codigo,cantidad:cantidad,unidad:unidad,lote_ref:lote,batch_ref:batch,observaciones:obs})}); var res=await r.json();
    if(res.ok){ var al=res.alerta?'<br><strong style="color:#e74c3c;">&#9888; '+res.alerta+'</strong>':''; if(msg)msg.innerHTML='<div class="alert-success">'+res.message+' - Stock: <strong>'+res.stock_nuevo+'</strong>'+al+'</div>'; var loteSave=lote; document.getElementById('mee-cantidad').value=''; document.getElementById('mee-lote').value=''; document.getElementById('mee-batch').value=''; document.getElementById('mee-obs').value=''; cargarMeeStock();cargarMeeAlertas();cargarMeeHistorial(); if(tipo==='Entrada'){window.open('/rotulo-recepcion-mee/'+encodeURIComponent(codigo)+'/'+cantidad+'?lote='+encodeURIComponent(loteSave),'_blank');}
    } else { if(msg)msg.innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>'; }
  }catch(e){if(msg)msg.innerHTML='<div class="alert-error">Error de conexion</div>';}
}
async function cargarMeeHistorial(){ try{ var r=await fetch('/api/mee/movimientos?limit=30'); var d=await r.json(); var tb=document.getElementById('mee-hist-tbody'); if(!tb) return;
  if(!d.movimientos||!d.movimientos.length){tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:#999;">Sin movimientos registrados</td></tr>';return;}
  var tC={Entrada:'#27ae60',Salida:'#e74c3c',Ajuste:'#9b59b6'}; var h='';
  d.movimientos.forEach(function(m){var c=tC[m.tipo]||'#555'; var ref=m.batch_ref||m.lote_ref||'';
    var btnRotulo=m.tipo==='Entrada'?'<button data-codigo="'+encodeURIComponent(m.mee_codigo)+'" data-cantidad="'+m.cantidad+'" data-lote="'+encodeURIComponent(ref||'')+'" onclick="abrirRotuloMEE(this)" style="background:#2B7A78;color:white;border:none;padding:4px 8px;font-size:0.75em;margin-right:4px;border-radius:3px;cursor:pointer;">&#128203; R&#243;tulo</button>':'';
    h+='<tr><td style="color:#bbb;font-size:0.8em;">#'+m.id+'</td><td style="font-family:monospace;font-size:0.82em;">'+m.mee_codigo+'</td><td style="font-size:0.85em;">'+m.descripcion+'</td><td><span style="color:'+c+';font-weight:700;font-size:0.88em;">'+m.tipo+'</span></td><td style="font-weight:700;">'+m.cantidad+' <span style="color:#999;font-size:0.8em;">'+m.unidad+'</span></td><td style="font-size:0.8em;color:#777;font-family:monospace;">'+(ref||'--')+'</td><td style="font-size:0.82em;">'+m.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(m.fecha?m.fecha.substring(0,16):'')+'</td><td>'+btnRotulo+'<button onclick="meeAnular('+m.id+')" style="background:#c0392b;padding:4px 8px;font-size:0.75em;">Anular</button></td></tr>';
  }); tb.innerHTML=h;
  }catch(e){}}
function abrirRotuloMEE(btn){
  var c=btn.getAttribute('data-codigo')||'';
  var q=btn.getAttribute('data-cantidad')||'1';
  var l=btn.getAttribute('data-lote')||'';
  window.open('/rotulo-recepcion-mee/'+c+'/'+q+'?lote='+l,'_blank');
}
async function meeAnular(id){ var m=prompt('Motivo de anulacion (obligatorio):'); if(!m||!m.trim()){alert('Debes ingresar un motivo.');return;}
  try{var r=await fetch('/api/mee/anular/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:m.trim()})}); var res=await r.json();
    if(res.ok){alert(res.message);cargarMeeHistorial();cargarMeeStock();cargarMeeAlertas();}else alert(res.error||'Error');
  }catch(e){alert('Error de conexion');}}
async function buscarTrazabilidadBatch(){ var b=(document.getElementById('mee-traz-batch')||{}).value||''; b=b.trim(); if(!b){alert('Ingresa un batch');return;}
  var res=document.getElementById('mee-traz-result'); if(res)res.innerHTML='<div style="color:#666;padding:10px;">Buscando...</div>';
  try{var r=await fetch('/api/mee/trazabilidad?batch='+encodeURIComponent(b)); var d=await r.json();
    if(!d.consumos||!d.consumos.length){if(res)res.innerHTML='<div style="color:#999;padding:10px 0;">Sin consumos para batch: <strong>'+b+'</strong></div>';return;}
    var h='<div style="background:white;border-radius:8px;padding:14px;margin-top:4px;"><h4 style="margin-bottom:10px;color:#155724;">Empaque consumido en batch: <strong>'+b+'</strong></h4><table class="table"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Cantidad</th><th>Responsable</th><th>Fecha</th></tr></thead><tbody>';
    d.consumos.forEach(function(c){h+='<tr><td style="font-family:monospace;font-size:0.82em;">'+c.mee_codigo+'</td><td>'+c.descripcion+'</td><td style="color:#777;font-size:0.8em;">'+c.categoria+'</td><td style="font-weight:700;">'+c.cantidad+' '+c.unidad+'</td><td>'+c.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(c.fecha?c.fecha.substring(0,16):'')+'</td></tr>';});
    h+='</tbody></table></div>'; if(res)res.innerHTML=h;
  }catch(e){if(res)res.innerHTML='<div style="color:#e74c3c;">Error</div>';}}
async function buscarTrazabilidadMee(){ var cod=(document.getElementById('mee-traz-codigo')||{}).value||''; cod=cod.trim(); if(!cod){alert('Ingresa un codigo MEE');return;}
  var res=document.getElementById('mee-traz-result'); if(res)res.innerHTML='<div style="color:#666;padding:10px;">Buscando...</div>';
  try{var r=await fetch('/api/mee/trazabilidad?codigo='+encodeURIComponent(cod)); var d=await r.json();
    if(!d.historial||!d.historial.length){if(res)res.innerHTML='<div style="color:#999;padding:10px 0;">Sin historial para MEE: <strong>'+cod+'</strong></div>';return;}
    var tC={Entrada:'#27ae60',Salida:'#e74c3c',Ajuste:'#9b59b6'};
    var h='<div style="background:white;border-radius:8px;padding:14px;margin-top:4px;"><h4 style="margin-bottom:10px;color:#155724;">Historial de: <strong>'+cod+'</strong></h4><table class="table"><thead><tr><th>Tipo</th><th>Cantidad</th><th>Lote</th><th>Batch Prod.</th><th>Responsable</th><th>Fecha</th></tr></thead><tbody>';
    d.historial.forEach(function(m){var c=tC[m.tipo]||'#555'; h+='<tr><td><span style="color:'+c+';font-weight:700;">'+m.tipo+'</span></td><td style="font-weight:700;">'+m.cantidad+' '+m.unidad+'</td><td style="font-size:0.82em;color:#777;">'+(m.lote_ref||'--')+'</td><td style="font-family:monospace;font-size:0.82em;">'+(m.batch_ref||'--')+'</td><td>'+m.responsable+'</td><td style="font-size:0.8em;color:#888;">'+(m.fecha?m.fecha.substring(0,16):'')+'</td></tr>';});
    h+='</tbody></table></div>'; if(res)res.innerHTML=h;
  }catch(e){if(res)res.innerHTML='<div style="color:#e74c3c;">Error</div>';}}


function _toast(msg,ok){var t=document.createElement("div");t.style="position:fixed;bottom:24px;right:24px;background:"+(ok?"#27ae60":"#c0392b")+";color:#fff;padding:14px 24px;border-radius:8px;z-index:9999;font-size:15px;font-weight:600;box-shadow:0 4px 14px rgba(0,0,0,0.2);max-width:360px;transition:opacity 0.3s;";t.textContent=msg;document.body.appendChild(t);setTimeout(function(){t.style.opacity="0";setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t);},300);},4000);}
function registrarAcond(){
  var d={lote:document.getElementById("ac-lote").value,producto:document.getElementById("ac-prod").value,presentacion:document.getElementById("ac-pres").value,cantidad_batch_g:parseFloat(document.getElementById("ac-batch").value)||0,unidades_producidas:parseInt(document.getElementById("ac-uds").value)||0,fecha:document.getElementById("ac-fecha").value,observaciones:document.getElementById("ac-obs").value};
  if(!d.lote||!d.producto){_toast("Lote y producto son obligatorios",0);return;}
  fetch("/api/acondicionamiento",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json();}).then(function(j){
    if(j.ok){_toast("\u2705 Batch registrado correctamente #"+j.id,1);["ac-lote","ac-prod","ac-pres","ac-batch","ac-uds","ac-obs"].forEach(function(i){document.getElementById(i).value="";});loadAcond();}
    else _toast("Error: "+(j.error||"desconocido"),0);
  }).catch(function(e){_toast("Error de red: "+e,0);});
}
function loadAcond(){
  fetch("/api/acondicionamiento").then(function(r){return r.json();}).then(function(rows){
    var tb=document.getElementById("ac-tbody"); if(!tb)return;
    tb.innerHTML="";
    rows.forEach(function(r){
      var estadoColor=r.estado==="Completado"?"#28a745":r.estado==="Rechazado"?"#dc3545":"#fd7e14";
      var btn="";
        if(r.estado==="En proceso") btn=`<button onclick="updateAcond(${r.id},'Completado')" style="background:#28a745;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px">Completar</button>`;
        tb.innerHTML+=`<tr><td style="padding:7px;border-bottom:1px solid #eee">${r.lote}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.producto}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.presentacion}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.cantidad_batch_g}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.unidades_producidas}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.fecha}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.operador}</td><td style="padding:7px;border-bottom:1px solid #eee"><span style="background:${estadoColor};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">${r.estado}</span></td><td style="padding:7px;border-bottom:1px solid #eee">${btn}</td></tr>`;
    });
  }).catch(function(){});
}
function updateAcond(id,estado){
  fetch("/api/acondicionamiento/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:estado})})
  .then(function(){loadAcond();});
}
function registrarLiberacion(){
  var d={lote:document.getElementById("lb-lote").value,producto:document.getElementById("lb-prod").value,presentacion:document.getElementById("lb-pres").value,unidades:parseInt(document.getElementById("lb-uds").value)||0,fecha_produccion:document.getElementById("lb-fprod").value,destino:document.getElementById("lb-dest").value,cliente:document.getElementById("lb-cli").value,observaciones:document.getElementById("lb-obs").value};
  if(!d.lote||!d.producto){_toast("Lote y producto son obligatorios",0);return;}
  fetch("/api/liberacion",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json();}).then(function(j){
    if(j.ok){_toast("\u2705 Lote enviado a CC #"+j.id,1);["lb-lote","lb-prod","lb-pres","lb-uds","lb-cli","lb-obs"].forEach(function(i){document.getElementById(i).value="";});loadLiberaciones("");}
    else _toast("Error: "+(j.error||"desconocido"),0);
  }).catch(function(e){_toast("Error: "+e,0);});
}
function loadLiberaciones(estado){
  var url="/api/liberacion"+(estado?"?estado="+encodeURIComponent(estado):"");
  fetch(url).then(function(r){return r.json();}).then(function(rows){
    var tb=document.getElementById("lb-tbody"); if(!tb)return;
    tb.innerHTML="";
    rows.forEach(function(r){
      var ec=r.estado==="Liberado"?"#28a745":r.estado==="Rechazado"?"#dc3545":"#fd7e14";
      var btns="";
      if(r.estado==="Pendiente CC"){
            btns=`<button onclick="aprobarLib(${r.id})" style="background:#28a745;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px;margin-right:3px">Liberar</button>`;
            btns+=`<button onclick="rechazarLib(${r.id})" style="background:#dc3545;color:#fff;border:none;border-radius:3px;padding:3px 7px;cursor:pointer;font-size:11px">Rechazar</button>`;
      }
        tb.innerHTML+=`<tr><td style="padding:7px;border-bottom:1px solid #eee">${r.lote}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.producto}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.unidades}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.destino}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.cliente||'--'}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.fecha_produccion||'--'}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.fecha_liberacion||'--'}</td><td style="padding:7px;border-bottom:1px solid #eee">${r.aprobado_por||'--'}</td><td style="padding:7px;border-bottom:1px solid #eee"><span style="background:${ec};color:#fff;padding:2px 7px;border-radius:10px;font-size:11px">${r.estado}</span></td><td style="padding:7px;border-bottom:1px solid #eee">${btns}</td></tr>`;
    });
  }).catch(function(){});
}
function aprobarLib(id){
  var cli=prompt("Cliente final (opcional):");
  fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:"Liberado",cliente:cli||""})})
  .then(function(){loadLiberaciones("");});
}
function rechazarLib(id){
  var obs=prompt("Motivo de rechazo:");
  if(!obs)return;
  fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:"Rechazado",observaciones:obs})})
  .then(function(){loadLiberaciones("");});
}

</script>
</body>
</html>
"""
