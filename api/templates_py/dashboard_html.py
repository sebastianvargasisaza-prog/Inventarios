# Auto-extraído de index.py — Fase A refactor
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover">
<meta name="theme-color" content="#7c3aed">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="EOS Planta">
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
<title>Planta - Espagiria Laboratorios</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos11">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<script>
// PWA: registrar service worker (Sebastian 30-abr-2026: "y si haz lo del mobil")
if('serviceWorker' in navigator){
  window.addEventListener('load',function(){
    navigator.serviceWorker.register('/static/sw.js').catch(function(e){console.log('SW reg fail',e);});
  });
}
</script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Segoe UI',sans-serif; background:#F5F4F0; min-height:100vh; padding:20px; }
.container { max-width:1400px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 20px 60px rgba(0,0,0,0.3); overflow:hidden; }

/* ── Mobile/tablet (Sebastian 30-abr-2026: "haz lo del mobil") ── */
@media (max-width: 768px) {
  body { padding:6px; }
  .container { border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); }
  .header { padding:14px 12px; }
  .header h1 { font-size:1.3em; }
  .tab-content { padding:12px 10px; }
  .tab-button { font-size:0.78em; padding:10px 8px; min-width:auto; }
  .grid { grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:8px; }
  .card { padding:12px; }
  .card p { font-size:1.4em; }
  /* Tablas se vuelven scrollables horizontal */
  .table-wrap, [style*="overflow-x:auto"] { -webkit-overflow-scrolling:touch; }
  .table { font-size:0.78em; }
  .table th, .table td { padding:6px 8px; }
  /* Reducir padding de modales */
  .modal-bk > div, [class*="modal"] > div { padding:14px !important; max-height:92vh; }
  /* Touch targets más grandes */
  button, .btn, [onclick] { min-height:38px; }
  input, select, textarea { font-size:16px !important; /* evita zoom iOS */ }
}
@media (max-width: 480px) {
  /* Tabs de programación más compactos */
  [id^="prog-tab-"] { padding:6px 10px !important; font-size:11px !important; }
  /* Stack vertical default en grids de 2 columnas */
  [style*="grid-template-columns:1fr 1fr"] { grid-template-columns:1fr !important; }
  [style*="grid-template-columns:repeat(4"] { grid-template-columns:repeat(2,1fr) !important; }
}
/* Safe area para iPhone notch */
@supports (padding: max(0px)) {
  body { padding-top:max(20px, env(safe-area-inset-top)); padding-bottom:max(20px, env(safe-area-inset-bottom)); }
}
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
<!-- Modal SOLICITAR (a nivel MP) -->
<div id="modal-solicitar-lote" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:0;max-width:560px;width:96%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="background:#27ae60;color:white;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;justify-content:space-between;align-items:center;">
      <h2 style="color:white;margin:0;font-size:1.2em;">&#128203; Solicitar Materia Prima</h2>
      <button onclick="cerrarSolicitarLote()" style="background:none;border:none;font-size:1.5em;cursor:pointer;color:white;padding:0 4px;line-height:1;" title="Cerrar">&#10005;</button>
    </div>
    <div style="padding:22px;">
      <p style="color:#888;font-size:0.85em;margin-bottom:14px;">Genera una solicitud de compra que llega al m&#243;dulo Compras. Se solicita la materia prima como tal — el lote es solo de referencia.</p>
      <div style="background:#f0f9f4;border:1px solid #c6e6d4;border-radius:8px;padding:12px;margin-bottom:14px;">
        <div style="font-size:0.78em;color:#1b5e20;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">Materia Prima</div>
        <div style="font-weight:700;color:#222;font-size:1.05em;" id="sol-mp-nombre">—</div>
        <div style="color:#666;font-size:0.85em;" id="sol-mp-cod">—</div>
        <div style="color:#888;font-size:0.78em;margin-top:4px;" id="sol-mp-stock">—</div>
      </div>
      <div class="form-group">
        <label>Proveedor</label>
        <input type="text" id="sol-prov" list="prov-list-global" placeholder="Selecciona del menu o escribe uno nuevo" autocomplete="off">
        <small id="sol-prov-hint" style="color:#888;font-size:0.78em;display:block;margin-top:4px;">Empieza a escribir para ver los existentes. Si falta uno, escr&iacute;belo y queda registrado.</small>
      </div>
      <div style="display:grid;grid-template-columns:2fr 1fr;gap:10px;">
        <div class="form-group"><label>Cantidad necesaria *</label><input type="number" id="sol-cant" placeholder="Ej: 5000" step="0.1" min="0.01"></div>
        <div class="form-group"><label>Unidad</label><select id="sol-unidad" style="width:100%;"><option value="g">g</option><option value="kg">kg</option><option value="und">und</option></select></div>
      </div>
      <div class="form-group"><label>Urgencia</label>
        <select id="sol-urg" style="width:100%;"><option value="Alta">Alta</option><option value="Normal" selected>Normal</option><option value="Baja">Baja</option></select>
      </div>
      <div class="form-group"><label>Observaci&#243;n / justificaci&#243;n *</label>
        <textarea id="sol-obs" rows="3" placeholder="Ej: Stock por debajo del m&#237;nimo, requerido para producci&#243;n GEL HID semana del 5 mayo"></textarea>
      </div>
      <div style="display:flex;gap:8px;margin-top:6px;">
        <button onclick="enviarSolicitarLote()" style="flex:1;background:#27ae60;padding:9px;font-weight:700;">&#10003; Enviar a Compras</button>
        <button onclick="cerrarSolicitarLote()" style="flex:1;background:#6c757d;padding:9px;">Cancelar</button>
      </div>
      <div id="sol-msg" style="margin-top:10px;font-size:0.85em;"></div>
    </div>
  </div>
</div>

<!-- Modal EDITAR PROVEEDOR (a nivel lote + catalogo) -->
<div id="modal-editar-prov" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:0;max-width:520px;width:96%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="background:#2B7A78;color:white;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;justify-content:space-between;align-items:center;">
      <h2 style="color:white;margin:0;font-size:1.2em;">&#9999;&#65039; Editar Proveedor</h2>
      <button onclick="cerrarEditarProveedor()" style="background:none;border:none;font-size:1.5em;cursor:pointer;color:white;padding:0 4px;line-height:1;" title="Cerrar">&#10005;</button>
    </div>
    <div style="padding:22px;">
      <div style="background:#f0f9f4;border:1px solid #c6e6d4;border-radius:8px;padding:12px;margin-bottom:14px;">
        <div style="font-size:0.78em;color:#1b5e20;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">Materia Prima / Lote</div>
        <div style="font-weight:700;color:#222;" id="ep-mp-info">—</div>
        <div style="color:#666;font-size:0.85em;margin-top:4px;" id="ep-prov-actual">—</div>
      </div>
      <p style="color:#666;font-size:0.85em;margin-bottom:8px;">Selecciona un proveedor existente del listado, o escribe uno nuevo si falta. El cambio aplica a <b>este lote</b> y al <b>cat&#225;logo de la MP</b> (futuras recepciones lo heredan correcto). Queda registrado en audit_log.</p>
      <div class="form-group">
        <label>Proveedor *</label>
        <input type="text" id="ep-input" list="prov-list-global" placeholder="Empieza a escribir o selecciona del menu" autocomplete="off" style="text-transform:none;">
        <datalist id="prov-list-global"></datalist>
        <small id="ep-hint" style="color:#888;font-size:0.78em;display:block;margin-top:4px;"></small>
      </div>
      <div style="display:flex;gap:8px;margin-top:6px;">
        <button onclick="guardarProveedor()" style="flex:1;background:#2B7A78;padding:9px;font-weight:700;color:white;">&#10003; Guardar</button>
        <button onclick="cerrarEditarProveedor()" style="flex:1;background:#6c757d;padding:9px;">Cancelar</button>
      </div>
      <div id="ep-msg" style="margin-top:10px;font-size:0.85em;"></div>
    </div>
  </div>
</div>

<!-- Modal LIMPIEZA PROVEEDORES — detecta duplicados y los unifica -->
<div id="modal-limpieza-prov" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:0;max-width:760px;width:96%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="background:#7c3aed;color:white;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;justify-content:space-between;align-items:center;">
      <h2 style="color:white;margin:0;font-size:1.2em;">&#129529; Limpieza de Proveedores</h2>
      <button onclick="cerrarLimpiezaProveedores()" style="background:none;border:none;font-size:1.5em;cursor:pointer;color:white;padding:0 4px;line-height:1;" title="Cerrar">&#10005;</button>
    </div>
    <div style="padding:22px;">
      <p style="color:#666;font-size:0.88em;margin-bottom:14px;">Grupos de proveedores que probablemente son el mismo escrito de distinta forma (mayuscula/minuscula, sufijos juridicos, espacios). Escoge el canonico de cada grupo y unifica — actualiza movimientos y catalogo de MPs.</p>
      <div id="lp-content" style="font-size:0.88em;">
        <div style="text-align:center;color:#888;padding:24px;">Detectando duplicados...</div>
      </div>
      <div style="display:flex;gap:8px;margin-top:14px;justify-content:flex-end;">
        <button onclick="cerrarLimpiezaProveedores()" style="background:#6c757d;padding:8px 16px;">Cerrar</button>
      </div>
    </div>
  </div>
</div>

<!-- Modal ELIMINAR LOTE (a nivel lote, motivo obligatorio) -->
<div id="modal-eliminar-lote" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9998;display:none;align-items:center;justify-content:center;">
  <div style="background:white;border-radius:16px;padding:0;max-width:520px;width:96%;max-height:90vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.5);">
    <div style="background:#c0392b;color:white;padding:18px 22px;border-radius:16px 16px 0 0;display:flex;justify-content:space-between;align-items:center;">
      <h2 style="color:white;margin:0;font-size:1.2em;">&#9888; Eliminar Lote</h2>
      <button onclick="cerrarEliminarLote()" style="background:none;border:none;font-size:1.5em;cursor:pointer;color:white;padding:0 4px;line-height:1;" title="Cerrar">&#10005;</button>
    </div>
    <div style="padding:22px;">
      <div style="background:#fff5f5;border:1px solid #f5c6cb;border-radius:8px;padding:12px;margin-bottom:14px;">
        <div style="font-size:0.78em;color:#922;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">Lote a eliminar</div>
        <div style="font-weight:700;color:#222;" id="del-mp-nombre">—</div>
        <div style="color:#666;font-size:0.85em;" id="del-mp-info">—</div>
      </div>
      <p style="color:#666;font-size:0.85em;margin-bottom:8px;"><b>Acci&#243;n permanente.</b> Borra todos los movimientos de este lote (entradas + salidas). El motivo queda registrado en audit_log para trazabilidad. Para correcciones de cantidad, mejor usa &laquo;Ajustar&raquo;.</p>
      <div class="form-group"><label style="color:#c0392b;font-weight:700;">Motivo de eliminaci&#243;n * (m&#237;n. 10 caracteres)</label>
        <textarea id="del-motivo" rows="3" placeholder="Ej: Recepci&#243;n duplicada — el mismo lote se carg&#243; el 18 y el 20 de abril por error"></textarea>
      </div>
      <div style="display:flex;gap:8px;margin-top:6px;">
        <button onclick="confirmarEliminarLote()" style="flex:1;background:#c0392b;padding:9px;font-weight:700;color:white;">&#128465; Confirmar eliminaci&#243;n</button>
        <button onclick="cerrarEliminarLote()" style="flex:1;background:#6c757d;padding:9px;">Cancelar</button>
      </div>
      <div id="del-msg" style="margin-top:10px;font-size:0.85em;"></div>
    </div>
  </div>
</div>

<div class="container">
  <header class="cx-mod-header cx-fade-in">
    <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
    <div>
      <div class="cx-mod-header__title">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M21 7.5l-9-5-9 5 9 5z"/><path d="M3 7.5v9l9 5 9-5v-9M12 12.5v9"/></svg>
        Planta
      </div>
      <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; Espagiria Laboratorios &middot; stock, lotes &amp; trazabilidad</div>
    </div>
    <div class="cx-mod-header__nav">
      <span id="oper-chip" class="cx-chip cx-chip-violet" style="display:none"></span>
      <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
      <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
      </button>
    </div>
  </header>
  <script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
  <div class="tabs">
    <button class="tab-button active" onclick="switchTab('dashboard',this)">&#128202; Dashboard</button>
    <button class="tab-button" onclick="switchGroup('bar-bodegaMP','stock',this)">&#128230; Bodega MP</button>
    <button class="tab-button" onclick="switchTab('empaque',this)">&#129492; Bodega MEE</button>
    <button class="tab-button" onclick="switchGroup('bar-prodHub','formulas',this)">&#127981; Producción</button>
    <button class="tab-button" onclick="switchGroup('bar-calidadHub','cuarentena',this)">&#128274; Calidad</button>
    <button class="tab-button" onclick="switchTab('programacion',this)">&#128225; Programación</button>
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
    <button class="sub-btn" onclick="subSwitchTab('produccion',this,'bar-prodHub')">&#127981; Fabricación</button>
    <button class="sub-btn" onclick="subSwitchTab('envasado',this,'bar-prodHub');loadColaSinEnvasar()">&#128230; Envasado</button>
    <button class="sub-btn" onclick="subSwitchTab('acondicionamiento',this,'bar-prodHub');loadColaAcond()">&#128295; Acondicionamiento</button>
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

    <!-- ═══ ZONA AHORA — qué requiere acción hoy ═══ -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:11px;font-weight:700;color:#dc2626;text-transform:uppercase;letter-spacing:1px;">
      <span style="width:8px;height:8px;background:#dc2626;border-radius:50%;display:inline-block;"></span>
      AHORA &middot; acción hoy
      <span style="flex:1;height:1px;background:#fecaca;"></span>
    </div>
    <div class="grid" style="margin-bottom:24px;grid-template-columns:repeat(3,1fr);">
      <div class="card" style="border-left:4px solid #dc2626;cursor:pointer;" onclick="switchGroup('bar-bodegaMP','alertas',null)"><h3>MPs sin stock</h3><p id="kpi-mps-sin-stock" style="color:#dc2626;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">críticas — bloquean producción</div></div>
      <div class="card" id="card-alertas" style="border-left:4px solid #f59e0b;cursor:pointer;" onclick="switchGroup('bar-bodegaMP','alertas',null)"><h3>MPs bajo mínimo</h3><p id="alertas-count" style="color:#e65100;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">incluye las en cero</div></div>
      <div class="card" style="border-left:4px solid #dc2626;"><h3>Lotes vencidos</h3><p id="kpi-lotes-vencidos" style="color:#dc2626;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">en bodega — dar de baja</div></div>
    </div>

    <!-- ═══ ZONA CERCA — próximos 7-30 días ═══ -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:11px;font-weight:700;color:#d97706;text-transform:uppercase;letter-spacing:1px;">
      <span style="width:8px;height:8px;background:#f59e0b;border-radius:50%;display:inline-block;"></span>
      CERCA &middot; próximos 7-30 días
      <span style="flex:1;height:1px;background:#fde68a;"></span>
    </div>
    <div class="grid" style="margin-bottom:24px;grid-template-columns:repeat(5,1fr);">
      <div class="card" style="border-left:4px solid #16a34a;cursor:pointer;" onclick="switchTab('programacion');" title="Programación / Checklist"><h3>Próximas a producir <span style="font-size:9px;color:#94a3b8;font-weight:500;">60d</span></h3><p id="producciones-proximas-count" style="color:#16a34a;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">click → checklist</div></div>
      <div class="card" style="border-left:4px solid #f59e0b;"><h3>Vencimientos &lt;30d</h3><p id="kpi-venc-criticos" style="color:#d97706;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">priorizar uso FEFO</div></div>
      <div class="card" style="border-left:4px solid #7c3aed;"><h3>Lotes en cuarentena</h3><p id="kpi-cuarentena" style="color:#7c3aed;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">esperando QC</div></div>
      <div class="card" style="border-left:4px solid #1e40af;cursor:pointer;" onclick="window.location.href='/recepcion'" title="Ir a Recepción"><h3>OCs en tránsito</h3><p id="kpi-ocs-transito" style="color:#1e40af;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">por recibir</div></div>
      <div class="card" style="border-left:4px solid #f59e0b;"><h3>MEE bajo mínimo</h3><p id="kpi-mees-bajo" style="color:#d97706;font-size:1.8em;">-</p><div style="font-size:10px;color:#78716c;">envases / etiquetas</div></div>
    </div>

    <!-- ═══ ZONA CONTEXTO — composición y tendencia ═══ -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;font-size:11px;font-weight:700;color:#6d28d9;text-transform:uppercase;letter-spacing:1px;">
      <span style="width:8px;height:8px;background:#6d28d9;border-radius:50%;display:inline-block;"></span>
      CONTEXTO &middot; composición y tendencia
      <span style="flex:1;height:1px;background:#e9d5ff;"></span>
    </div>
    <div class="grid" style="margin-bottom:20px;grid-template-columns:repeat(3,1fr);">
      <div class="card"><h3>Stock total</h3><p id="stock-total" style="font-size:1.4em;">-</p><div style="font-size:10px;color:#78716c;">en gramos · MPs activas</div></div>
      <div class="card"><h3>Lotes en bodega</h3><p id="materiales-count" style="font-size:1.4em;">-</p><div style="font-size:10px;color:#78716c;">total movimientos registrados</div></div>
      <div class="card"><h3>Producciones (histórico)</h3><p id="producciones-count" style="font-size:1.4em;">-</p><div style="font-size:10px;color:#78716c;">producciones realizadas total</div></div>
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
      <div style="display:flex;gap:10px;"><button onclick="loadStock()">&#8635; Actualizar</button><button onclick="exportarExcelStock()" style="background:#217346;">&#128196; Descargar Excel</button><button onclick="abrirLimpiezaProveedores()" style="background:#7c3aed;" title="Detecta proveedores duplicados por typo y los unifica">&#129529; Limpiar proveedores</button></div>
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
        <th style="text-align:right;">Dias</th><th style="text-align:center;">Estado</th><th style="text-align:center;">Ajuste</th><th style="text-align:center;">Historial</th><th style="text-align:center;">Solicitar</th><th style="text-align:center;">Eliminar</th>
      </tr></thead>
      <tbody id="stock-body"><tr><td colspan="17" style="text-align:center;color:#999;padding:20px;">Cargando...</td></tr></tbody>
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
        <div><label style="font-size:0.82em;font-weight:700;display:block;margin-bottom:4px;">Proveedor</label><input type="text" id="nmee-prov" list="prov-list-global" placeholder="Selecciona o escribe nuevo" autocomplete="off"></div>
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
        <div class="form-group">
          <label>Tipo de Material *</label>
          <select id="nmp-tipo-mat" style="width:100%;padding:8px;border:1px solid #dde;border-radius:6px;">
            <option value="MP">&#129516; Materia Prima</option>
            <option value="Envase Primario">&#127881; Envase Primario (frasco, tubo)</option>
            <option value="Envase Secundario">&#128230; Envase Secundario (caja, display)</option>
            <option value="Empaque">&#127991; Empaque (etiqueta, inserto, sello)</option>
          </select>
        </div>
        <div class="form-group"><label>Subtipo / categor&#237;a</label><input type="text" id="nmp-tipo" placeholder="Ej: Activo, Emoliente, Conservante..."></div>
        <div class="form-group"><label>Proveedor</label><input type="text" id="nmp-prov" list="prov-list-global" placeholder="Selecciona o escribe nuevo" autocomplete="off"></div>
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
        <div class="form-group"><label>Proveedor</label><input type="text" id="ing-prov" list="prov-list-global" placeholder="Auto — selecciona o escribe nuevo" autocomplete="off"></div>
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
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:10px">
      <h2 style="margin:0">&#129514; Formulas Maestras de Produccion</h2>
      <button onclick="abrirNuevoProducto()" style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;border:none;padding:9px 18px;border-radius:6px;font-size:13px;font-weight:800;cursor:pointer;box-shadow:0 2px 6px rgba(8,145,178,.3)">🚀 Lanzar producto nuevo</button>
    </div>
    <p style="color:#666;margin-bottom:18px;">Define la receta de cada producto. Al registrar una produccion, las MPs se descuentan automaticamente del inventario. Para <b>lanzamientos nuevos</b> usa "🚀 Lanzar producto nuevo" — crea fórmula + config + (opcional) primera producción prioritaria.</p>
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
    <div style="display:flex;gap:10px;flex-wrap:wrap;">
      <button onclick="simularProduccion()" style="background:#6c5ce7;">&#128269; Verificar Stock</button>
      <button onclick="iniciarRegistroProd()">&#9989; Registrar Produccion</button>
      <button onclick="abrirRotulos()" style="background:#c0392b;">&#128209; Generar Rotulos</button>
    </div>
    <div id="prod-simul-result" style="margin-top:12px;"></div>
    <div id="prod-msg"></div>
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

    <!-- Filtro por tipo de material — inventario cíclico de E&E -->
    <div style="background:#fff7e6;border:1px solid #ffd58a;border-radius:10px;padding:14px 18px;margin-bottom:14px;">
      <div style="font-weight:700;color:#7a4a00;font-size:0.92em;margin-bottom:10px;">
        &#128230; Filtrar conteo por tipo de material
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;" id="cnt-tipo-tabs">
        <button onclick="setConteoTipo('')" data-tipo="" class="cnt-tipo-tab active"
                style="padding:8px 16px;border:2px solid #2B7A78;background:#2B7A78;color:#fff;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;">
          &#128203; Todos
        </button>
        <button onclick="setConteoTipo('MP')" data-tipo="MP" class="cnt-tipo-tab"
                style="padding:8px 16px;border:2px solid #dde;background:#fff;color:#555;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;">
          &#129516; Materias Primas
        </button>
        <button onclick="setConteoTipo('Envase Primario')" data-tipo="Envase Primario" class="cnt-tipo-tab"
                style="padding:8px 16px;border:2px solid #dde;background:#fff;color:#555;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;">
          &#127881; Envase Primario
        </button>
        <button onclick="setConteoTipo('Envase Secundario')" data-tipo="Envase Secundario" class="cnt-tipo-tab"
                style="padding:8px 16px;border:2px solid #dde;background:#fff;color:#555;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;">
          &#128230; Envase Secundario
        </button>
        <button onclick="setConteoTipo('Empaque')" data-tipo="Empaque" class="cnt-tipo-tab"
                style="padding:8px 16px;border:2px solid #dde;background:#fff;color:#555;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;">
          &#127991; Empaque
        </button>
      </div>
      <div style="font-size:0.78em;color:#7a4a00;margin-top:8px;">
        Selecciona el tipo y luego elige una estanter&#237;a — el conteo se enfoca solo en ese tipo.
      </div>
    </div>

    <!-- Selector de estanteria manual -->
    <div style="background:#f8f9ff;border:1px solid #dde;border-radius:10px;padding:18px;margin-bottom:20px;display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:end;">
      <div>
        <label style="display:block;font-weight:600;margin-bottom:4px;font-size:0.88em;color:#555;">
          Estanteria / Seccion a contar
          <span id="cnt-tipo-label" style="display:none;color:#2B7A78;font-weight:700;margin-left:6px;"></span>
        </label>
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
            <th>Codigo</th><th>Material</th>
            <th>Lote</th>
            <th>Proveedor</th>
            <th style="text-align:right;">Stock Sistema (g)</th>
            <th style="text-align:right;width:130px;">Stock Fisico (g)</th>
            <th style="text-align:right;">Diferencia</th>
            <th>%</th>
            <th style="width:140px;">Causa</th>
            <th style="text-align:center;">Acciones</th>
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
        <div style="display:flex;gap:8px;margin-bottom:10px;align-items:center;flex-wrap:wrap">
          <select id="mee-cat-filter-bodega" style="flex:1;min-width:180px;width:auto;" onchange="cargarMeeStock()"><option value="">Todas las categorias</option></select>
          <input id="mee-search-input" type="text" placeholder="Buscar..." oninput="cargarMeeStock()" style="padding:7px 10px;border:1px solid #d6d3d1;border-radius:6px;font-size:13px">
          <button onclick="cargarMeeStock()" style="white-space:nowrap;background:#15803d;color:#fff;">&#8635; Actualizar</button>
          <button onclick="meeImportarExcel()" style="white-space:nowrap;background:#7c3aed;color:#fff;" title="Importar inventario desde scripts/mee_excel_import.json (admin)">&#128194; Importar Excel</button>
          <button onclick="meeAgrupadoToggle()" id="mee-agrupado-btn" style="white-space:nowrap;background:#0891b2;color:#fff;">&#128221; Agrupado</button>
        </div>
        <div style="overflow-x:auto;">
          <table class="table" id="mee-tabla-estandar"><thead><tr><th>Codigo</th><th>Descripcion</th><th>Categoria</th><th>Stock</th><th>Minimo</th><th>Estado</th><th>Proveedor</th><th>Acciones</th></tr></thead>
          <tbody id="mee-stock-tbody"><tr><td colspan="8" style="text-align:center;color:#999;">Cargando...</td></tr></tbody></table>
        </div>
        <div id="mee-agrupado-wrap" style="display:none"></div>
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

<div id="envasado" class="tab-content">
<div style="padding:18px">
  <h2 style="margin:0 0 4px;color:#1a4a7a">&#128230; Envasado</h2>
  <p style="color:#666;font-size:13px;margin-bottom:16px">Registra el uso de envases y tapas por lote de produccion terminado.</p>

  <div id="cola-sin-envasar" style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;padding:14px;margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <h3 style="margin:0;font-size:14px;color:#1b5e20">&#128230; Cola: lotes listos para envasar</h3>
      <button onclick="loadColaSinEnvasar()" style="background:#1b5e20;color:#fff;border:none;border-radius:4px;padding:4px 12px;font-size:12px;cursor:pointer">&#8635; Actualizar</button>
    </div>
    <div id="cola-env-tbody-wrap" style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="background:#2e7d32;color:#fff">
          <th style="padding:7px">Lote</th><th style="padding:7px">Producto</th><th style="padding:7px">Batch (kg)</th><th style="padding:7px">Fecha</th><th style="padding:7px">Operador</th><th style="padding:7px">Accion</th>
        </tr></thead>
        <tbody id="cola-env-tbody"><tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Panel activo de envasado — aparece al hacer clic en Envasar desde la cola -->
  <div id="env-panel-activo" style="display:none;background:#fff;border:2px solid #1a4a7a;border-radius:10px;padding:18px;margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h3 style="margin:0;color:#1a4a7a;font-size:15px">&#128230; Envasando lote de produccion</h3>
        <div style="font-size:13px;color:#444;margin-top:4px">
          Producto: <strong id="env-act-prod" style="color:#1a4a7a"></strong> &nbsp;·&nbsp;
          Lote: <strong id="env-act-lote"></strong> &nbsp;·&nbsp;
          Batch: <strong id="env-act-batch"></strong>
        </div>
        <input type="hidden" id="env-act-prod-id">
        <input type="hidden" id="env-act-prod-raw">
      </div>
      <button onclick="cerrarEnvActivo()" style="background:#6c757d;color:#fff;border:none;border-radius:5px;padding:6px 14px;font-size:12px;cursor:pointer">&#10005; Cancelar</button>
    </div>
    <div id="env-pres-rows"></div>
    <button onclick="addPresRow()" style="background:transparent;border:2px dashed #1a4a7a;color:#1a4a7a;border-radius:6px;padding:7px 18px;font-size:13px;cursor:pointer;margin-bottom:14px;width:100%">+ Agregar presentacion</button>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
      <button onclick="registrarEnvasadoMulti()" style="background:#1a4a7a;color:#fff;border:none;border-radius:6px;padding:10px 26px;font-size:14px;font-weight:700;cursor:pointer">&#9989; Registrar Envasado</button>
      <div id="env-act-msg" style="font-size:13px"></div>
    </div>
  </div>

  <div id="env-form-old" style="display:none;background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">
    <h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Envasado</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Producto</label>
        <select id="env-prod-sel" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
          <option value="">-- Selecciona producto --</option>
        </select>
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Lote</label>
        <input id="env-lote" placeholder="Ej: ESP260425LBHA" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Unidades envasadas</label>
        <input id="env-uds" type="number" min="1" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Presentacion</label>
        <input id="env-pres" placeholder="Ej: Frasco 30ml" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Envase usado (MEE)</label>
        <select id="env-envase-sel" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
          <option value="">-- Tipo de envase --</option>
        </select>
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Tapa usada (MEE)</label>
        <select id="env-tapa-sel" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
          <option value="">-- Tipo de tapa --</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:10px">
      <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Observaciones</label>
      <textarea id="env-obs" rows="2" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px"></textarea>
    </div>
    <button onclick="registrarEnvasadoSimple()" style="background:#1a4a7a;color:#fff;padding:9px 22px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;font-size:13px">&#9989; Registrar Envasado</button>
    <div id="env-msg" style="margin-top:8px;font-size:13px"></div>
  </div>

  <div id="env-historial">
    <h3 style="margin:0 0 10px;color:#2B7A78;font-size:14px">&#128202; Historial Envasado</h3>
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="background:#1a4a7a;color:#fff">
            <th style="padding:8px">Lote</th>
            <th style="padding:8px">Producto</th>
            <th style="padding:8px">Presentacion</th>
            <th style="padding:8px">Uds</th>
            <th style="padding:8px">Envase</th>
            <th style="padding:8px">Tapa</th>
            <th style="padding:8px">Fecha</th>
            <th style="padding:8px">Operador</th>
          </tr>
        </thead>
        <tbody id="env-tbody"></tbody>
      </table>
    </div>
  </div>
</div>
</div>

<div id="acondicionamiento" class="tab-content">
<div style="padding:18px">
  <h2 style="margin:0 0 4px;color:#1a4a7a">&#128295; Acondicionamiento PT</h2>
  <p style="color:#666;font-size:13px;margin-bottom:16px">Registra etiquetas, plegadizas y unidades salientes para entrega al cliente.</p>

  <div id="cola-sin-acond" style="background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;padding:14px;margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <h3 style="margin:0;font-size:14px;color:#0d47a1">&#128295; Cola: lotes listos para acondicionar</h3>
      <button onclick="loadColaAcond()" style="background:#0d47a1;color:#fff;border:none;border-radius:4px;padding:4px 12px;font-size:12px;cursor:pointer">&#8635; Actualizar</button>
    </div>
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead><tr style="background:#1565c0;color:#fff">
          <th style="padding:7px">Lote</th><th style="padding:7px">Producto</th><th style="padding:7px">Uds</th><th style="padding:7px">Presentacion</th><th style="padding:7px">Fecha</th><th style="padding:7px">Accion</th>
        </tr></thead>
        <tbody id="cola-acond-tbody"><tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- Panel activo de acondicionamiento — aparece al clic en Acondicionar desde la cola -->
  <div id="ac-panel-activo" style="display:none;background:#fff;border:2px solid #0d47a1;border-radius:10px;padding:18px;margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;flex-wrap:wrap;gap:8px">
      <div>
        <h3 style="margin:0;color:#0d47a1;font-size:15px">&#128295; Acondicionando lote</h3>
        <div style="font-size:13px;color:#444;margin-top:4px">
          Producto: <strong id="ac-act-prod" style="color:#0d47a1"></strong> &nbsp;&middot;&nbsp;
          Lote: <strong id="ac-act-lote"></strong> &nbsp;&middot;&nbsp;
          <span id="ac-act-uds-info" style="color:#555"></span>
        </div>
        <input type="hidden" id="ac-act-env-id">
        <input type="hidden" id="ac-act-lote-raw">
        <input type="hidden" id="ac-act-prod-raw">
      </div>
      <button onclick="cerrarAcondActivo()" style="background:#6c757d;color:#fff;border:none;border-radius:5px;padding:6px 14px;font-size:12px;cursor:pointer">&#10005; Cancelar</button>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Fecha</label>
        <input id="ac-act-fecha" type="date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Destino / Cliente</label>
        <input id="ac-act-destino" placeholder="ANIMUS Lab / nombre cliente" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
    </div>
    <div id="ac-pres-rows" style="margin-bottom:10px"></div>
    <button onclick="addAcPresRow()" style="background:transparent;border:2px dashed #0d47a1;color:#0d47a1;border-radius:6px;padding:7px 18px;font-size:13px;cursor:pointer;margin-bottom:14px;width:100%">+ Agregar presentacion</button>
    <div style="margin-bottom:12px">
      <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Observaciones</label>
      <textarea id="ac-act-obs" rows="2" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px"></textarea>
    </div>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
      <button onclick="registrarAcondDesdePanel()" style="background:#0d47a1;color:#fff;border:none;border-radius:6px;padding:10px 26px;font-size:14px;font-weight:700;cursor:pointer">&#9989; Registrar Acondicionamiento</button>
      <div id="ac-act-msg" style="font-size:13px"></div>
    </div>
  </div>

  <div id="ac-form-manual" style="background:#f0f4f8;border-radius:8px;padding:16px;margin-bottom:18px">
    <h3 style="margin:0 0 12px;font-size:14px;color:#333">Registrar Acondicionamiento</h3>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Producto</label>
        <select id="ac-prod-sel" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
          <option value="">-- Selecciona producto --</option>
        </select>
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Lote PT</label>
        <input id="ac-lote" placeholder="Ej: ESP260425LBHA" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Unidades acondicionadas</label>
        <input id="ac-uds" type="number" min="1" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Fecha</label>
        <input id="ac-fecha" type="date" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Etiquetas usadas</label>
        <input id="ac-etiquetas" type="number" min="0" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Plegadizas usadas</label>
        <input id="ac-plegadizas" type="number" min="0" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Destino / Cliente</label>
        <input id="ac-destino" placeholder="ANIMUS Lab / nombre cliente" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
      <div>
        <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">SKU PT</label>
        <input id="ac-sku" placeholder="LBHA-30ML" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px">
      </div>
    </div>
    <div style="margin-bottom:10px">
      <label style="font-size:12px;color:#555;font-weight:600;display:block;margin-bottom:3px">Observaciones</label>
      <textarea id="ac-obs" rows="2" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:13px"></textarea>
    </div>
    <button onclick="registrarAcondSimple()" style="background:#1a4a7a;color:#fff;padding:9px 22px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;font-size:13px">&#9989; Registrar Batch</button>
    <div id="ac-form-msg" style="margin-top:8px;font-size:13px"></div>
  </div>

  <div id="ac-table-wrap">
    <h3 style="margin:0 0 10px;color:#2B7A78;font-size:14px">&#128202; Historial Acondicionamiento</h3>
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="background:#1a4a7a;color:#fff">
            <th style="padding:8px">Lote</th>
            <th style="padding:8px">Producto</th>
            <th style="padding:8px">Uds</th>
            <th style="padding:8px">Etiquetas</th>
            <th style="padding:8px">Plegadizas</th>
            <th style="padding:8px">Destino</th>
            <th style="padding:8px">Fecha</th>
            <th style="padding:8px">Operador</th>
          </tr>
        </thead>
        <tbody id="ac-tbody"></tbody>
      </table>
    </div>
  </div>
</div>
</div>

<div id="programacion" class="tab-content">
<div style="padding:18px">
  <!-- 4 pestañas únicas (Sebastian 30-abr-2026: "reduce a las pestañas necesarias") -->
  <div style="display:flex;gap:10px;margin-bottom:18px;border-bottom:2px solid #e2e8f0;padding-bottom:12px;align-items:center;flex-wrap:wrap">
    <button id="prog-tab-planv2" onclick="switchProgTab('planv2')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;box-shadow:0 3px 10px rgba(8,145,178,.35)">
      &#128197; Plan
    </button>
    <button id="prog-tab-asignacion" onclick="switchProgTab('asignacion')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#1a4a7a">
      &#128205; Asignación Semanal
    </button>
    <button id="prog-tab-mando" onclick="switchProgTab('mando')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#1a4a7a">
      &#127919; Centro de Mando <span style="font-size:9px;font-weight:600;background:#dc2626;color:#fff;padding:1px 6px;border-radius:6px;margin-left:4px;text-transform:uppercase;letter-spacing:.5px">live</span>
    </button>
    <button id="prog-tab-autoplan" onclick="switchProgTab('autoplan')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:800;cursor:pointer;background:linear-gradient(135deg,#7c3aed,#dc2626);color:#fff;box-shadow:0 3px 10px rgba(124,58,237,.4)">
      &#129302; Auto-Plan
    </button>
    <button id="prog-tab-maquila" onclick="switchProgTab('maquila')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#1a4a7a">
      &#129309; Maquila
    </button>
    <button id="prog-tab-config" onclick="switchProgTab('config')"
      style="padding:9px 22px;border:none;border-radius:8px 8px 0 0;font-size:14px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#1a4a7a">
      &#9881; Configuración
    </button>
    <span id="prog-tareas-badge" style="display:none;background:#dc2626;color:#fff;font-size:9px;font-weight:800;padding:2px 8px;border-radius:8px"></span>
  </div>
  <!-- Botones HIDDEN para no romper switchProgTab() y JS existente -->
  <div style="display:none">
    <button id="prog-tab-centro"></button>
    <button id="prog-tab-plan"></button>
    <button id="prog-tab-checklist"></button>
    <button id="prog-tab-tareas"></button>
    <button id="prog-tab-plano"></button>
    <button id="prog-tab-presentaciones"></button>
    <button id="prog-tab-equipos"></button>
    <button id="prog-tab-preflight"></button>
    <button id="prog-tab-plansem"></button>
    <button id="prog-tab-conteo"></button>
  </div>

  <div id="ptab-centro" style="display:none">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px">
    <div>
      <h2 style="margin:0 0 4px;color:#1a4a7a">&#128225; Centro de Programación</h2>
      <p style="color:#666;font-size:13px;margin:0">Shopify + Calendário + Fórmulas + Stock — en tiempo real</p>
    </div>

  </div>

  <!-- Semáforo de estado general -->
  <div id="prog-semaforo" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px">
    <div style="background:#f0f4f8;border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;margin-bottom:4px">&#128225;</div>
      <div style="font-size:12px;color:#666">Velocidad Shopify</div>
      <div id="prog-vel-val" style="font-size:1.4em;font-weight:700;color:#1a4a7a">--</div>
      <div id="prog-vel-sub" style="font-size:11px;color:#888">unidades / mes</div>
    </div>
    <div style="background:#f0f4f8;border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;margin-bottom:4px">&#128197;</div>
      <div style="font-size:12px;color:#666">Próxima Producción</div>
      <div id="prog-cal-val" style="font-size:1.1em;font-weight:700;color:#1a4a7a">--</div>
      <div id="prog-cal-sub" style="font-size:11px;color:#888">según calendario</div>
    </div>
    <div style="background:#f0f4f8;border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;margin-bottom:4px">&#128202;</div>
      <div style="font-size:12px;color:#666">Productos con Alerta</div>
      <div id="prog-alert-val" style="font-size:1.4em;font-weight:700;color:#dc3545">--</div>
      <div id="prog-alert-sub" style="font-size:11px;color:#888">requieren acción</div>
    </div>
    <div style="background:#f0f4f8;border-radius:8px;padding:14px;text-align:center">
      <div style="font-size:28px;margin-bottom:4px">&#129302;</div>
      <div style="font-size:12px;color:#666">IA Análisis</div>
      <div id="prog-ia-status" style="font-size:0.85em;color:#888;font-style:italic">Cargando...</div>
    </div>
  </div>

  <!-- Warnings de integridad (alias collisions, calendar fail, velocidad pobre, fórmulas incompletas) -->
  <div id="prog-warnings" style="display:none"></div>

  <!-- Narrative IA -->
  <div id="prog-ia-box" style="background:linear-gradient(135deg,#0f2d1f,#1a4a7a);border-radius:10px;padding:18px;margin-bottom:20px;display:none">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      <span style="font-size:20px">&#129302;</span>
      <span style="color:#4ade80;font-weight:700;font-size:14px">Análisis IA — Centro de Programación</span>
    </div>
    <div id="prog-ia-text" style="color:#e2e8f0;font-size:13px;line-height:1.6"></div>
  </div>

  <!-- Tabla de proyección por producto -->
  <div style="background:#fff;border:1px solid #e0e0e0;border-radius:10px;overflow:hidden;margin-bottom:20px">
    <div style="background:#1a4a7a;color:#fff;padding:12px 16px;font-weight:600;font-size:13px">
      📦 Proyección de Stock — Faltante a 15 / 30 / 60 días por producto
    </div>
    <div id="prog-tabla-wrap" style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="background:#f5f7fa;color:#444">
            <th style="padding:10px;text-align:left;border-bottom:1px solid #eee">Producto / SKU</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Stock (uds)</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Venta/mes</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Días Cobertura</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee;background:#fef3c7;color:#92400e">Falta 15d</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee;background:#fed7aa;color:#9a3412">Falta 30d</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee;background:#fecaca;color:#7f1d1d">Falta 60d</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Prox. Producción</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Calendario</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Materias Primas</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Estado</th>
            <th style="padding:10px;text-align:center;border-bottom:1px solid #eee">Acción</th>
          </tr>
        </thead>
        <tbody id="prog-tbody">
          <tr><td colspan="11" style="text-align:center;padding:30px;color:#aaa;font-style:italic">
            Haz clic en "Actualizar" para cargar la proyección
          </td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Alertas de abastecimiento -->
  <div style="background:#fff;border:1px solid #e0e0e0;border-radius:10px;overflow:hidden">
    <div style="background:#dc3545;color:#fff;padding:12px 16px;font-weight:600;font-size:13px">
      🚨 Alertas de Abastecimiento
    </div>
    <div id="prog-alertas" style="padding:16px">
      <div style="text-align:center;color:#aaa;font-style:italic;padding:20px">Sin alertas — actualiza para verificar</div>
    </div>
  </div>

  <!-- MP Bridge — enlaces formula ↔ bodega -->
  <div id="bridge-panel" style="background:#fff;border:1px solid #e0e0e0;border-radius:10px;overflow:hidden;margin-top:16px">
    <div style="background:#5c3317;color:#fff;padding:12px 16px;font-weight:600;font-size:13px;display:flex;align-items:center;justify-content:space-between">
      <span>&#128279; Enlace Fórmula ↔ Bodega MP</span>
      <button onclick="toggleBridgePanel()" style="background:rgba(255,255,255,0.2);border:none;color:#fff;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:12px">&#9660; Ver / Ocultar</button>
    </div>
    <div id="bridge-panel-body" style="display:none">
      <div style="padding:14px;background:#fdf8f3;border-bottom:1px solid #e0e0e0;font-size:12px;color:#666">
        <b>¿Para qué sirve esto?</b> Cuando un ingrediente de fórmula no aparece en Bodega MP por nombre diferente (ej: "Silicona Líquida" vs "Dimethicone BM 96-350"), aquí puedes vincularlo manualmente. Una vez enlazado, el semáforo de MPs usará el stock real.
      </div>
      <!-- Unmatched list -->
      <div id="bridge-unmatched-wrap" style="padding:14px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
          <b style="font-size:13px">MPs sin enlazar</b>
          <button onclick="cargarUnmatched(this)" style="background:#5c3317;color:#fff;border:none;border-radius:5px;padding:5px 12px;cursor:pointer;font-size:12px">&#128260; Cargar</button>
          <span id="unmatched-count" style="font-size:12px;color:#888"></span>
        </div>
        <div id="unmatched-list"></div>
      </div>
      <!-- Existing bridge mappings -->
      <div style="border-top:1px solid #e0e0e0;padding:14px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
          <b style="font-size:13px">Mapeos activos</b>
          <button onclick="cargarBridgeMappings()" style="background:#2B7A78;color:#fff;border:none;border-radius:5px;padding:5px 12px;cursor:pointer;font-size:12px">&#128260; Actualizar</button>
        </div>
        <div id="bridge-mappings-list"><div style="color:#aaa;font-style:italic;font-size:12px">— carga para ver —</div></div>
      </div>
    </div>
  </div>
<script>
var fData=[], allStock=[], _cat={}, _ultimoIng=null;
var formulasPin=false;
var _lotes=[], _lotesFull=[], _meeData=[], _prodPendiente=null;
var OPER_ACTUAL='{usuario}';
document.addEventListener('DOMContentLoaded',function(){
  // Restaurar operador desde localStorage si no vino por sesión
  if(!OPER_ACTUAL){
    try{var saved=localStorage.getItem('espagiria_operador');if(saved)OPER_ACTUAL=saved;}catch(e){}
  }
  // Pre-cargar lista de proveedores para los datalists (recepcion, catalogo,
  // editar lote, solicitar). Idempotente: si ya se cargo, no hace nada.
  if(typeof _cargarProveedoresUnicos==='function'){_cargarProveedoresUnicos();}
  var c=document.getElementById('oper-chip');
  if(OPER_ACTUAL){
    if(c) c.innerHTML='<span onclick="cambiarOperador()" title="Cambiar operador" style="cursor:pointer;">&#128100; '+OPER_ACTUAL+' <span style="font-size:0.75em;opacity:0.7;">[cambiar]</span></span>';
    loadDashboardCompleto();loadFormulas();
  setTimeout(cargarEnvasadoSimpleTab, 1500);
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

// ─── Solicitar MP (a nivel materia prima, no lote) ─────────────────────────
var _solLote=null;
function abrirSolicitarLote(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _solLote=i;
  document.getElementById('sol-mp-nombre').textContent=(i.material_nombre||'')+(i.nombre_inci?' ('+i.nombre_inci+')':'');
  document.getElementById('sol-mp-cod').textContent='Codigo: '+(i.material_id||'-');
  var stock_label='Stock min: '+(i.stock_min_g||0).toLocaleString()+' g';
  if(i.lote){stock_label+=' · Lote ref.: '+i.lote;}
  document.getElementById('sol-mp-stock').textContent=stock_label;
  document.getElementById('sol-prov').value=i.proveedor||'';
  document.getElementById('sol-cant').value='';
  document.getElementById('sol-unidad').value='g';
  document.getElementById('sol-urg').value='Normal';
  document.getElementById('sol-obs').value='';
  document.getElementById('sol-msg').innerHTML='';
  // Cargar proveedores existentes en el desplegable (mismo datalist global
  // que usa Editar Proveedor) — evita typos y registra implicitamente
  // proveedores nuevos cuando el usuario escribe uno que no esta en la lista.
  _cargarProveedoresUnicos();
  document.getElementById('modal-solicitar-lote').style.display='flex';
}
function cerrarSolicitarLote(){document.getElementById('modal-solicitar-lote').style.display='none';_solLote=null;}
async function enviarSolicitarLote(){
  if(!_solLote)return;
  var msg=document.getElementById('sol-msg');
  var prov=document.getElementById('sol-prov').value.trim();
  var cant=parseFloat(document.getElementById('sol-cant').value||0);
  var und=document.getElementById('sol-unidad').value;
  var urg=document.getElementById('sol-urg').value;
  var obs=document.getElementById('sol-obs').value.trim();
  if(!cant||cant<=0){msg.innerHTML='<span style="color:#c00;">Cantidad debe ser mayor a 0.</span>';return;}
  if(obs.length<5){msg.innerHTML='<span style="color:#c00;">Justificacion requerida (min. 5 chars).</span>';return;}
  // Convertir a gramos para solicitudes_compra (cantidad_g)
  var cant_g=cant; if(und==='kg')cant_g=cant*1000;
  var obs_full=obs+(prov?(' · Proveedor sugerido: '+prov):'');
  var payload={
    solicitante:(window.OPER_ACTUAL||window._usuario||'planta'),
    urgencia:urg,
    observaciones:obs_full,
    empresa:'Espagiria',
    categoria:'Materia Prima',
    tipo:'Compra',
    area:'Produccion',
    items:[{
      codigo_mp:_solLote.material_id,
      nombre_mp:_solLote.material_nombre,
      cantidad_g:cant_g,
      unidad:und,
      justificacion:obs,
      valor_estimado:0
    }]
  };
  msg.innerHTML='<span style="color:#666;">Enviando...</span>';
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Solicitud creada')+'. Llega a Compras.</span>';
      setTimeout(cerrarSolicitarLote,1800);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
}

// ─── Editar Proveedor (afecta lote + catalogo MP) ──────────────────────────
var _epLote=null; var _epProveedoresCargados=false;
async function _cargarProveedoresUnicos(){
  if(_epProveedoresCargados)return;
  try{
    var r=await fetch('/api/proveedores-unicos');
    if(!r.ok)return;
    var d=await r.json();
    var dl=document.getElementById('prov-list-global');
    if(!dl)return;
    dl.innerHTML='';
    (d.proveedores||[]).forEach(function(p){
      var o=document.createElement('option'); o.value=p; dl.appendChild(o);
    });
    _epProveedoresCargados=true;
  }catch(e){/* no critico */}
}
function abrirEditarProveedor(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _epLote=i;
  var info=(i.material_nombre||'')+' · '+(i.material_id||'');
  if(i.lote)info+=' · Lote '+i.lote;
  document.getElementById('ep-mp-info').textContent=info;
  document.getElementById('ep-prov-actual').textContent='Proveedor actual: '+(i.proveedor||'(vacio)');
  document.getElementById('ep-input').value=i.proveedor||'';
  document.getElementById('ep-msg').innerHTML='';
  document.getElementById('ep-hint').textContent='Sugerencia: usa el desplegable para evitar duplicados por typo.';
  _cargarProveedoresUnicos();
  document.getElementById('modal-editar-prov').style.display='flex';
  setTimeout(function(){var el=document.getElementById('ep-input');if(el)el.focus();},120);
}
function cerrarEditarProveedor(){document.getElementById('modal-editar-prov').style.display='none';_epLote=null;}
async function guardarProveedor(){
  if(!_epLote)return;
  var msg=document.getElementById('ep-msg');
  var nuevo=document.getElementById('ep-input').value.trim();
  if(nuevo.length<2){msg.innerHTML='<span style="color:#c00;">Proveedor debe tener al menos 2 caracteres.</span>';return;}
  if(nuevo===(_epLote.proveedor||'')){msg.innerHTML='<span style="color:#888;">Sin cambios — el proveedor es el mismo.</span>';return;}
  msg.innerHTML='<span style="color:#666;">Guardando...</span>';
  var loteSeg=_epLote.lote||'_SIN_LOTE_';
  var url='/api/lotes/'+encodeURIComponent(_epLote.material_id)+'/'+encodeURIComponent(loteSeg)+'/proveedor';
  try{
    var r=await fetch(url,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({proveedor:nuevo})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Proveedor actualizado')+'</span>';
      _epProveedoresCargados=false; // re-cargar lista la proxima vez (incluye nuevo si lo creo)
      setTimeout(function(){cerrarEditarProveedor();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+(d.detail?' — '+d.detail:'')+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
}

// ─── Limpieza de Proveedores (detectar y unificar duplicados) ──────────────
function _escHTML(s){return String(s||'').replace(/[&<>"']/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];});}
async function abrirLimpiezaProveedores(){
  document.getElementById('modal-limpieza-prov').style.display='flex';
  await _renderLimpiezaProveedores();
}
function cerrarLimpiezaProveedores(){
  document.getElementById('modal-limpieza-prov').style.display='none';
  // Refrescar datalist global por si hubo cambios
  _epProveedoresCargados=false;
  _cargarProveedoresUnicos();
}
async function _renderLimpiezaProveedores(){
  var cont=document.getElementById('lp-content');
  cont.innerHTML='<div style="text-align:center;color:#888;padding:24px;">Detectando duplicados...</div>';
  try{
    var r=await fetch('/api/proveedores-duplicados');
    var d=await r.json();
    var grupos=d.grupos||[];
    if(!grupos.length){
      cont.innerHTML='<div style="text-align:center;color:#1a8a1a;padding:24px;font-weight:700;">&#10003; Sin duplicados detectados — todos los proveedores tienen formato unico.</div>';
      return;
    }
    var html='<div style="margin-bottom:8px;color:#7c3aed;font-weight:700;">'+grupos.length+' grupo(s) con variantes</div>';
    grupos.forEach(function(g,gi){
      html+='<div id="lp-grupo-'+gi+'" style="border:1px solid #ddd;border-radius:8px;padding:12px;margin-bottom:10px;background:#fafafa;">';
      html+='<div style="font-size:0.78em;color:#888;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;">'+g.count_variantes+' variantes &middot; clave: <code>'+_escHTML(g.clave_normalizada)+'</code></div>';
      html+='<div style="margin-bottom:8px;">';
      g.variantes.forEach(function(v,vi){
        var uso=g.usos[v]||0;
        var checked=(v===g.canonico_sugerido)?'checked':'';
        html+='<label style="display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer;">';
        html+='<input type="radio" name="lp-canon-'+gi+'" value="'+_escHTML(v)+'" '+checked+'>';
        html+='<span style="flex:1;"><b>'+_escHTML(v)+'</b> <span style="color:#888;font-size:0.85em;">('+uso+' mov)</span></span>';
        html+='</label>';
      });
      html+='</div>';
      html+='<div id="lp-msg-'+gi+'" style="font-size:0.85em;margin-bottom:6px;"></div>';
      html+='<button onclick="unificarGrupo('+gi+')" style="background:#7c3aed;color:white;padding:6px 12px;font-size:0.85em;border-radius:6px;">&#128279; Unificar este grupo</button>';
      html+='</div>';
    });
    cont.innerHTML=html;
    // Guardamos los grupos en una variable global para acceder desde unificarGrupo
    window._lpGrupos=grupos;
  }catch(e){
    cont.innerHTML='<div style="color:#c00;padding:24px;">Error: '+e.message+'</div>';
  }
}
async function unificarGrupo(gi){
  var grupos=window._lpGrupos||[]; var g=grupos[gi]; if(!g)return;
  var radios=document.getElementsByName('lp-canon-'+gi);
  var canonico='';
  for(var i=0;i<radios.length;i++){if(radios[i].checked){canonico=radios[i].value;break;}}
  if(!canonico){alert('Selecciona el proveedor canonico');return;}
  if(!confirm('Unificar todas las variantes a "'+canonico+'"?\\n\\nEsto actualiza movimientos + catalogo de MPs. Reversible solo via audit_log.')){return;}
  var msg=document.getElementById('lp-msg-'+gi);
  msg.innerHTML='<span style="color:#666;">Unificando...</span>';
  try{
    var r=await fetch('/api/proveedores-unificar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({canonico:canonico,variantes:g.variantes})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Unificado')+'</span>';
      // Re-render despues de un momento
      setTimeout(function(){_renderLimpiezaProveedores();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
}

// ─── Eliminar Lote (a nivel lote, motivo obligatorio) ──────────────────────
var _delLote=null;
function abrirEliminarLote(idx){
  var i=_lotes[idx]; if(!i){alert('Lote no encontrado'); return;}
  _delLote=i;
  document.getElementById('del-mp-nombre').textContent=(i.material_nombre||'')+' · '+(i.material_id||'');
  var partes=[];
  if(i.lote)partes.push('Lote: '+i.lote); else partes.push('Lote: (sin lote)');
  partes.push('Cantidad actual: '+(i.cantidad_g||0).toLocaleString()+' g');
  if(i.fecha_vencimiento)partes.push('Vence: '+i.fecha_vencimiento);
  if(i.proveedor)partes.push('Prov.: '+i.proveedor);
  document.getElementById('del-mp-info').textContent=partes.join(' · ');
  document.getElementById('del-motivo').value='';
  document.getElementById('del-msg').innerHTML='';
  document.getElementById('modal-eliminar-lote').style.display='flex';
}
function cerrarEliminarLote(){document.getElementById('modal-eliminar-lote').style.display='none';_delLote=null;}
async function confirmarEliminarLote(){
  if(!_delLote)return;
  var msg=document.getElementById('del-msg');
  var motivo=document.getElementById('del-motivo').value.trim();
  if(motivo.length<10){msg.innerHTML='<span style="color:#c00;">Motivo min. 10 caracteres.</span>';return;}
  if(!confirm('Eliminar definitivamente el lote '+(_delLote.lote||'(sin lote)')+' de '+_delLote.material_nombre+'? Esta accion borra todos los movimientos asociados.')){return;}
  msg.innerHTML='<span style="color:#666;">Eliminando...</span>';
  var loteSeg=_delLote.lote||'_SIN_LOTE_';
  var url='/api/lotes/'+encodeURIComponent(_delLote.material_id)+'/'+encodeURIComponent(loteSeg);
  try{
    var r=await fetch(url,{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({motivo:motivo})});
    var d=await r.json();
    if(r.ok){
      msg.innerHTML='<span style="color:#1a8a1a;font-weight:700;">✓ '+(d.message||'Lote eliminado')+'</span>';
      setTimeout(function(){cerrarEliminarLote();loadStock();},1500);
    }else{
      msg.innerHTML='<span style="color:#c00;">Error: '+(d.error||r.status)+(d.detail?' — '+d.detail:'')+'</span>';
    }
  }catch(e){
    msg.innerHTML='<span style="color:#c00;">Error de red: '+e.message+'</span>';
  }
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
var _provSaveTimers={};
function guardarProveedorMP(inp){
  var cod=inp.dataset.cod;
  var val=inp.value.trim();
  if(!cod) return;
  inp.style.borderColor='#ffc107';
  inp.title='Guardando...';
  clearTimeout(_provSaveTimers[cod]);
  _provSaveTimers[cod]=setTimeout(function(){
    fetch('/api/maestro-mps/'+encodeURIComponent(cod)+'/proveedor',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({proveedor:val})
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){
        inp.style.borderColor='#28a745';
        inp.title=val ? 'Guardado en maestro y directorio de proveedores' : 'Proveedor borrado';
        setTimeout(function(){ inp.style.borderColor=''; inp.title='Edita y presiona Enter o Tab para guardar'; },2500);
        // Actualizar _alertasData para que solicitarTodasMPs use datos frescos
        var ad=window._alertasData||[];
        var found=ad.find(function(a){return a.codigo_mp===cod;});
        if(found) found.proveedor=val;
        // Actualizar datalist de compras si esta disponible
        if(window._proveedoresList && val && !window._proveedoresList.includes(val)){
          window._proveedoresList.push(val);
        }
        if(val) _toast('Proveedor guardado: '+val,1);
      } else {
        inp.style.borderColor='#dc3545';
        inp.title='Error: '+(d.error||'desconocido');
        _toast('Error guardando proveedor: '+(d.error||''), 0);
      }
    }).catch(function(e){
      inp.style.borderColor='#dc3545';
      inp.title='Error de conexion';
      _toast('Error de conexion al guardar proveedor', 0);
    });
  },700);
}

async function solicitarTodasMPs(){
  var alertas=(window._alertasData||[]).filter(function(a){return a.tipo!=='MEE';});
  if(!alertas.length){alert('No hay MPs bajo minimo para solicitar.');return;}
  var sinProv=alertas.filter(function(a){return !a.proveedor;});
  if(sinProv.length){
    var names=sinProv.slice(0,5).map(function(a){return a.nombre;}).join(', ');
    if(!confirm('Hay '+sinProv.length+' MP(s) sin proveedor asignado: '+names+'. Se incluiran de todas formas. Continuar?')) return;
  }
  var sol=OPER_ACTUAL||'Planta';
  var items=alertas.map(function(a){
    return {codigo_mp:a.codigo_mp,nombre_mp:a.nombre,cantidad_g:a.deficit>0?a.deficit:a.stock_minimo,
            unidad:'g',justificacion:'Bajo stock minimo. Stock actual: '+a.stock_actual+'g / Minimo: '+a.stock_minimo+'g'};
  });
  var data={solicitante:sol,empresa:'Espagiria',area:'Produccion',
            categoria:'Materia Prima',tipo:'Compra',urgencia:'Alta',
            observaciones:'Solicitud automatica desde alertas de stock — '+items.length+' MPs',
            items:items};
  try{
    var r=await fetch('/api/solicitudes-compra',{method:'POST',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok&&res.numero){
      alert('Solicitud '+res.numero+' enviada a Compras con '+items.length+' MPs. En Compras > Tab Planta podras asignar precios y generar OCs por proveedor.');
    } else {
      alert('Error: '+(res.error||'desconocido'));
    }
  }catch(e){alert('Error de red: '+e.message);}
}

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
  var btn=document.querySelector("#modal-solicitud-compra button");
  if(btn){btn.disabled=true;btn.textContent="Enviando..."}
  try{
    var urgEl=document.getElementById("sol-urgencia");
    var obsEl=document.getElementById("sol-obs");
    var data={solicitante:nom,empresa:"Espagiria",
      urgencia:urgEl?urgEl.value:"Normal",
      observaciones:obsEl?obsEl.value:"",
      items:[{codigo_mp:(_solMP&&_solMP.cod)||"S/C",nombre_mp:(_solMP&&_solMP.nom)||"Sin nombre",
              cantidad_g:cant,unidad:"g",justificacion:"Solicitud desde alertas de stock"}]};
    var r=await fetch("/api/solicitudes-compra",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    var res=null;
    try{res=await r.json();}catch(_){res=null;}
    if(r.ok&&res){
      document.getElementById("sol-msg").innerHTML='<div style="padding:12px;background:#d4edda;border:1px solid #28a745;border-radius:6px;color:#155724;font-weight:600;">&#10003; Solicitud '+res.numero+' creada. El equipo de compras fue notificado.</div>';
      if(btn){btn.disabled=true;btn.textContent="\u2713 Enviado";btn.style.background="#28a745";}
      setTimeout(function(){cerrarSolicitudCompra();},3500);
    } else {
      var errMsg=(res&&res.error)?res.error:(res&&res.detail)?res.detail.slice(-200):"Error "+r.status+" — recarga la pagina e intenta de nuevo";
      document.getElementById("sol-msg").innerHTML='<div style="padding:10px;background:#f8d7da;border:1px solid #dc3545;border-radius:6px;color:#721c24;font-size:0.88em;">&#10060; '+errMsg+'</div>';
      if(btn){btn.disabled=false;btn.textContent="\u2713 Enviar Solicitud";}
    }
  }catch(e){
    document.getElementById("sol-msg").innerHTML='<div style="padding:10px;background:#f8d7da;border:1px solid #dc3545;border-radius:6px;color:#721c24;">&#10060; Error: '+e.message+'</div>';
    if(btn){btn.disabled=false;btn.textContent="✓ Enviar Solicitud";}
  }
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
  if(n==='alertas'){ loadVenc30(); loadAlertasMEE(); }
  if(n==='stock') loadMEE();
  if(n==='acondicionamiento'){loadAcond();cargarMeeParaAcond();}
  if(n==='liberacion'){loadLiberaciones('');cargarClientesLib();}
  if(n==='movimientos') loadMovimientos();
  if(n==='produccion') cargarHistProd();
  if(n==='movimientos') loadMovimientos();
  if(n==='programacion'){
    cargarProgramacion(null);
    // Sebastian (30-abr-2026): "las pestañas no sirven" — al click "Programación"
    // forzar que se muestre Plan v2 (no la pestaña Centro vieja).
    if(typeof switchProgTab==='function') switchProgTab('planv2');
  }
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
  if(tabId==='envasado') cargarEnvasadoSimpleTab();
  if(tabId==='acondicionamiento') cargarAcondSimpleTab();
  if(tabId==='programacion') cargarProgramacion(null);
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
    document.getElementById('stock-total').textContent=Math.round(d.stock_total||0).toLocaleString('es-CO')+' g';
    document.getElementById('materiales-count').textContent=d.movimientos||'0';
    var elProx=document.getElementById('producciones-proximas-count');
    if(elProx){
      var nProx = d.producciones_proximas||0;
      elProx.textContent = nProx;
      elProx.style.color = nProx>0 ? '#16a34a' : '#94a3b8';
    }
    document.getElementById('producciones-count').textContent=d.producciones||'0';

    // KPIs nuevos del dashboard replanteado en zonas AHORA/CERCA/CONTEXTO
    var k = d.kpis || {ahora:{}, cerca:{}, contexto:{}};
    function setKpi(id, val, fallbackZero){
      var el = document.getElementById(id);
      if(!el) return;
      var n = val||0;
      el.textContent = n;
      // Atenuar si está en cero (visual: todo OK)
      if(fallbackZero && n===0) el.style.opacity = '0.4';
      else el.style.opacity = '1';
    }
    var a = k.ahora || {};
    setKpi('kpi-mps-sin-stock', a.mps_sin_stock, true);
    setKpi('kpi-lotes-vencidos', a.lotes_vencidos, true);
    var ce = k.cerca || {};
    setKpi('kpi-venc-criticos', ce.venc_criticos_30d, true);
    setKpi('kpi-cuarentena', ce.lotes_cuarentena, true);
    setKpi('kpi-ocs-transito', ce.ocs_en_transito, true);
    setKpi('kpi-mees-bajo', ce.mees_bajo_minimo, true);
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
    document.getElementById('stock-body').innerHTML='<tr><td colspan="17" style="padding:20px;color:#c00;">Error al cargar.</td></tr>';
  }
}
function renderStock(items){
  var tb=document.getElementById('stock-body');
  if(!items.length){tb.innerHTML='<tr><td colspan="17" style="text-align:center;color:#999;padding:20px;">Sin datos</td></tr>';return;}
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
    h+='<td style="color:#555;">'+(i.proveedor||'<span style="color:#bbb;">— sin proveedor —</span>')+' <button onclick="abrirEditarProveedor('+gi+')" title="Editar proveedor" style="margin-left:4px;padding:1px 6px;font-size:0.75em;background:#e8f5f5;color:#2B7A78;border:1px solid #b8dada;border-radius:4px;cursor:pointer;">&#9999;&#65039;</button></td>';
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
    h+='<td style="text-align:center;"><button onclick="abrirSolicitarLote('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#27ae60;color:#fff;border-radius:4px;">Solicitar</button></td>';
    h+='<td style="text-align:center;"><button onclick="abrirEliminarLote('+gi+')" style="padding:3px 9px;font-size:0.75em;background:#c0392b;color:#fff;border-radius:4px;">Eliminar</button></td>';
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
  cargarOCsPendientes();
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
function buscarMPIngreso(val){
  val=(val||'').trim();
  var st=document.getElementById('ing-status'),panel=document.getElementById('ing-nueva-mp-inline'),dd=document.getElementById('mp-dropdown');
  if(val.length<2){
    if(st)st.textContent='';
    ['ing-inci','ing-nombre','ing-tipo'].forEach(function(id){var el=document.getElementById(id);if(el)el.value='';});
    if(panel)panel.style.display='none';
    if(dd)dd.style.display='none';
    return;
  }
  // Use cached catalog (_cat loaded by initIngreso) — avoids HTTP request on every keypress
  var mps=Object.values(_cat);
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
        var kg=((item.cantidad_g||0)/1000).toFixed(2);
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
  // B4: disable button to prevent double-submission
  var btn=document.querySelector('button[onclick="registrarIngreso()"]');
  if(btn){btn.disabled=true;btn.textContent='Registrando...';}
  try{
    var r=await fetch('/api/recepcion',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    var res=await r.json();
    if(r.ok){
      _ultimoIng=res;
      var ocWarn=res.oc_warning?'<br><span style="color:#e65100;font-size:0.9em;">⚠ '+res.oc_warning+'</span>':'';
      var successMsg='<div class="alert-success">'+res.message+(enCuarentena?' — CUARENTENA activa':'')+ocWarn+'</div>';
      limpiarIngreso();
      // Show success AFTER limpiarIngreso so it is not wiped immediately
      document.getElementById('ing-msg').innerHTML=successMsg;
      // Re-enable button so user can register another MP
      if(btn){btn.disabled=false;btn.textContent='✓ Registrar Entrada';}
      await cargarHistIngreso();
      await cargarOCsPendientes();
    } else {
      document.getElementById('ing-msg').innerHTML='<div class="alert-error">'+(res.error||'Error al registrar')+'</div>';
      if(btn){btn.disabled=false;btn.textContent='\u2713 Registrar Entrada';}
    }
  }catch(e){
    document.getElementById('ing-msg').innerHTML='<div class="alert-error">Error de red: '+e.message+'</div>';
    if(btn){btn.disabled=false;btn.textContent='\u2713 Registrar Entrada';}
  }
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
  if(!formulasPin){
    html+='<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:10px 15px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;">'
         +'<span>&#128274; Cantidades ocultas &mdash; activa el PIN para ver la f&oacute;rmula completa</span>'
         +'<button onclick="pedirPinFormula()" style="background:#667eea;color:white;border:none;padding:5px 14px;border-radius:4px;cursor:pointer;font-weight:600;font-size:0.85em;">&#128275; Desbloquear</button>'
         +'</div>';
  } else {
    html+='<div style="background:#d4edda;border:1px solid #28a745;border-radius:6px;padding:8px 15px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;">'
         +'<span style="color:#155724;">&#128275; F&oacute;rmulas desbloqueadas</span>'
         +'<button onclick="formulasPin=false;renderFormulas(fData)" style="background:#6c757d;color:white;border:none;padding:5px 14px;border-radius:4px;cursor:pointer;font-size:0.85em;">&#128274; Bloquear</button>'
         +'</div>';
  }
  var MASK='<span style="filter:blur(5px);user-select:none;pointer-events:none;color:#555;">&#x2588;&#x2588;.&#x2588;&#x2588;</span>';
  fl.forEach(function(f,idx){
    var total=f.items.reduce(function(s,i){return s+i.porcentaje;},0);
    var ok=Math.abs(total-100)<0.1;
    var rows='';
    f.items.forEach(function(it){
      var pctVal=formulasPin?it.porcentaje+'%':MASK+'%';
      var gVal=formulasPin?(it.porcentaje*10).toFixed(2)+'g':MASK+'g';
      rows+='<tr><td style="font-family:monospace;">'+it.material_id+'</td><td>'+it.material_nombre+'</td><td>'+pctVal+'</td><td style="font-weight:600;">'+gVal+'</td></tr>';
    });
    var totalStr=formulasPin?total.toFixed(2)+'%'+(ok?' OK':' revisar'):MASK+'%';
    var editBtn=formulasPin
      ?'<button onclick="editFormula('+idx+')" style="background:#667eea;padding:5px 10px;font-size:0.82em;">Editar</button>'
      :'<button onclick="pedirPinFormula()" style="background:#aaa;color:white;border:none;padding:5px 10px;font-size:0.82em;border-radius:3px;cursor:pointer;" title="Requiere PIN">&#128274; Editar</button>';
    html+='<div style="border:1px solid #dde;border-radius:8px;padding:15px;margin-bottom:12px;background:white;">';
    html+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">';
    html+='<h4 style="color:#667eea;">'+f.producto_nombre+' <span style="font-weight:normal;color:#888;font-size:0.82em;">(base '+f.unidad_base_g+'g)</span></h4>';
    html+='<div style="display:flex;gap:6px;">'+editBtn;
    html+='<button onclick="delFormula('+idx+')" style="background:#cc4444;padding:5px 10px;font-size:0.82em;">Eliminar</button>';
    html+='</div></div>';
    html+='<table class="table" style="font-size:0.85em;"><thead><tr><th>Codigo MP</th><th>Material</th><th>%</th><th>g/kg</th></tr></thead><tbody>'+rows+'</tbody></table>';
    html+='<small style="color:'+(ok?'#28a745':'#e68a00')+';"> '+totalStr+'</small>';
    html+='</div>';
  });
  c.innerHTML=html;
}

async function pedirPinFormula(){
  var pin=prompt('PIN de acceso a f\u00f3rmulas:');
  if(!pin) return;
  try{
    var r=await fetch('/api/formulas/unlock',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:pin})});
    if(r.ok){formulasPin=true;renderFormulas(fData);}
    else{alert('PIN incorrecto');}
  }catch(e){alert('Error al verificar PIN');}
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
  if(!formulasPin){pedirPinFormula();return;}
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
  // Validacion: advertir si la cantidad parece inusualmente alta
  if(kg>1000){
    var msg='\u26a0\ufe0f ADVERTENCIA: Ingresaste '+kg.toLocaleString()+' kg de producci\u00f3n.';
    msg+=' | Equivale a '+(kg*1000).toLocaleString()+' g.';
    msg+=' | Las producciones normales son menores a 1,000 kg. Confirmar?';
    msg+=' | Si querias gramos, divide entre 1000 (ej: 20 kg = ingresa 20).';
    if(!confirm(msg)) return;
  }
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
      var provId='prov-inp-'+a.codigo_mp.replace(/[^a-zA-Z0-9]/g,'');
      h+='<td style="min-width:140px;">';
      h+='<input type="text" id="'+provId+'" value="'+(a.proveedor||'')+'"';
      h+=' data-cod="'+a.codigo_mp+'"';
      h+=' placeholder="Sin proveedor"';
      h+=' style="width:100%;padding:3px 6px;border:1px solid #ccc;border-radius:4px;font-size:0.82em;"';
      h+=' onchange="guardarProveedorMP(this)" oninput="guardarProveedorMP(this)"';
      h+=' title="Edita y presiona Enter o Tab para guardar">';
      h+='</td>';
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
  var obs=document.getElementById('prod-obs').value;
  var pres=document.getElementById('prod-presentacion').value;
  try{
    var r=await fetch('/api/produccion',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({producto:prod,cantidad_kg:kg,observaciones:obs,presentacion:pres,operador:OPER_ACTUAL})});
    var d=await r.json();
    if(!r.ok){document.getElementById('prod-msg').innerHTML='<span style="color:red;">'+(d.error||'Error')+'</span>';return;}
    var html='<div class="alert-success">'+(d.message||'Produccion registrada')+' &mdash; Lote: <strong>'+d.lote+'</strong></div>';
    if(d.descuentos&&d.descuentos.length){
      html+='<div style="margin-top:8px;font-size:0.88em;color:#555;"><strong>MPs descontadas:</strong><ul style="margin-top:4px;padding-left:18px;">';
      d.descuentos.forEach(function(mp){html+='<li>'+mp.material+': '+mp.cantidad_g.toLocaleString()+'g</li>';});
      html+='</ul></div>';
    }
    html+='<div style="margin-top:8px;padding:8px 14px;background:#e8f4fd;border-radius:6px;font-size:0.85em;color:#1a4a7a;">';
    html+='&#8594; Ve a <strong>Acondicionamiento</strong> para registrar cada presentacion, descontar MEE y crear Stock PT.</div>';
    document.getElementById('prod-msg').innerHTML=html;
    document.getElementById('prod-preview').style.display='none';
    document.getElementById('prod-sel').value='';
    document.getElementById('prod-manual').value='';
    document.getElementById('prod-kg').value='';
    document.getElementById('prod-obs').value='';
    cargarHistProd();
    setTimeout(function(){document.getElementById('prod-msg').innerHTML='';},10000);
  }catch(e){document.getElementById('prod-msg').innerHTML='<span style="color:red;">Error: '+e.message+'</span>';}
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
  var tipoMatEl=document.getElementById('nmp-tipo-mat');
  var tipoMaterial=tipoMatEl ? (tipoMatEl.value || 'MP') : 'MP';
  var data={codigo_mp:cod,nombre_inci:inci,nombre_comercial:nombre,
    tipo:(document.getElementById('nmp-tipo').value||'').trim(),
    tipo_material:tipoMaterial,
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
      html+='<div><b>Cantidad:</b> '+(p.cantidad_kg?Math.round(Number(p.cantidad_kg)*1000).toLocaleString('es-CO')+' g':'&#8212;')+'</div>';
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
// Filtro actual de tipo_material: '' = todos, 'MP' / 'Envase Primario' /
// 'Envase Secundario' / 'Empaque'
var _conteoTipoFiltro = '';

function setConteoTipo(tipo){
  _conteoTipoFiltro = tipo || '';
  // Marcar tab activo
  document.querySelectorAll('#cnt-tipo-tabs .cnt-tipo-tab').forEach(function(b){
    var isActive = (b.getAttribute('data-tipo') || '') === _conteoTipoFiltro;
    if(isActive){
      b.style.background = '#2B7A78';
      b.style.color = '#fff';
      b.style.borderColor = '#2B7A78';
      b.classList.add('active');
    } else {
      b.style.background = '#fff';
      b.style.color = '#555';
      b.style.borderColor = '#dde';
      b.classList.remove('active');
    }
  });
  // Mostrar etiqueta del tipo seleccionado
  var lbl = document.getElementById('cnt-tipo-label');
  if(lbl){
    if(_conteoTipoFiltro){
      lbl.textContent = '· tipo: ' + _conteoTipoFiltro;
      lbl.style.display = 'inline';
    } else {
      lbl.style.display = 'none';
    }
  }
  // Recargar estanterías + programación cíclica con filtro aplicado
  cargarEstanterias();
  cargarProgramacionCiclica();
}

function _esTipoEE(tipo){
  if(!tipo) return false;
  var t = tipo.toLowerCase();
  return t.indexOf('envase') >= 0 || t.indexOf('empaque') >= 0;
}

async function cargarEstanterias(){
  var sel = document.getElementById('cnt-est-sel');
  if(!sel) return;
  // Si el filtro es E&E, el selector de estantería NO aplica (no hay
  // localización). Mostramos un único option informativo y dejamos que
  // el usuario use el botón "Iniciar" de la fila "Esta semana" arriba.
  if(_esTipoEE(_conteoTipoFiltro)){
    while(sel.options.length > 1) sel.remove(1);
    sel.options[0].textContent = '— No aplica para E&E (cuenta los 3 items asignados arriba)';
    sel.disabled = true;
    return;
  }
  sel.disabled = false;
  if(sel.options[0]) sel.options[0].textContent = '-- Selecciona estanteria --';
  try{
    var url = '/api/conteo/estanterias';
    if(_conteoTipoFiltro){
      url += '?tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    var data = await r.json();
    while(sel.options.length > 1) sel.remove(1);
    if(!data || data.length === 0){
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = _conteoTipoFiltro
        ? '(sin estanterías para tipo "' + _conteoTipoFiltro + '")'
        : '(sin estanterías con stock)';
      opt.disabled = true;
      sel.appendChild(opt);
      return;
    }
    data.forEach(function(e){
      var opt = document.createElement('option');
      opt.value = e.estanteria;
      opt.textContent = e.estanteria + ' (' + e.total_mps + ' items, ' + Math.round(e.stock_total||0).toLocaleString('es-CO') + ' g)';
      sel.appendChild(opt);
    });
  }catch(e){}
}

async function cargarProgramacionCiclica(){
  try{
    // El endpoint cambia de comportamiento según tipo_material:
    //   sin filtro o 'MP'  → rotación por estantería (modo legacy)
    //   E&E (Envase/Empaque) → rotación de 3 ítems determinista por semana
    var url = '/api/conteo/programacion';
    if(_conteoTipoFiltro && _conteoTipoFiltro !== 'MP'){
      url += '?tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    var d = await r.json();
    var tbody = document.getElementById('cnt-prog-rows');
    if(!tbody) return;
    if(!d.semanas || d.semanas.length === 0){
      var msg = d.mensaje || 'Sin datos de estanter&iacute;as';
      var html = '<tr><td colspan="5" style="padding:18px;background:#fffaf2;border:1px dashed #f0c674;">';
      html += '<div style="font-size:14px;font-weight:600;color:#8b5a00;margin-bottom:8px;">&#x26A0; '+msg+'</div>';
      if(d.diagnostico){
        var dx = d.diagnostico;
        html += '<div style="font-size:12px;color:#555;line-height:1.7;">';
        html += '<div><strong>Catálogo total:</strong> '+dx.total_catalogo+' items activos</div>';
        if(dx.sin_clasificar > 0){
          html += '<div style="color:#b94400;"><strong>'+dx.sin_clasificar+' items</strong> sin tipo asignado (“MP” por defecto)</div>';
        }
        if(dx.tipos_existentes && dx.tipos_existentes.length){
          html += '<div style="margin-top:6px;"><strong>Tipos actualmente en catálogo:</strong></div>';
          html += '<ul style="margin:4px 0 8px 22px;color:#444;">';
          dx.tipos_existentes.forEach(function(t){
            html += '<li><code style="background:#f3f0ea;padding:1px 6px;border-radius:3px;">'+t.tipo+'</code> &mdash; '+t.total+' items</li>';
          });
          html += '</ul>';
        }
        html += '<div style="margin-top:10px;padding:10px 12px;background:#fff;border-left:3px solid #2B7A78;color:#1f5f5b;">'
              + '<strong>Acción sugerida:</strong> '+dx.accion_sugerida+'</div>';
        html += '<div style="margin-top:10px;"><a href="/admin" target="_blank" '
              + 'style="display:inline-block;background:#2B7A78;color:#fff;padding:6px 14px;border-radius:6px;font-size:12px;text-decoration:none;font-weight:600;">'
              + 'Abrir /admin &raquo; tab Banco / diagnóstico</a> '
              + '<span style="margin-left:8px;font-size:11px;color:#888;">(o ir directo al Catálogo MPs en Planta)</span></div>';
        html += '</div>';
      }
      html += '</td></tr>';
      tbody.innerHTML = html;
      return;
    }
    var modoItems = (d.modo === 'items');
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
        accion = '<button onclick="iniciarConteoProgramado(\\''+s.estanteria+'\\')" style="padding:4px 12px;background:#2B7A78;color:#fff;border:none;border-radius:6px;font-size:0.82em;cursor:pointer;">'+(s.conteo_estado==='Abierto'?'Retomar':'Iniciar')+'</button>';
      }
      // En modo items, mostrar los códigos+nombres de los 3 ítems en lugar
      // del label sintético "E&E-Empaque-S05"
      var asignacionTxt;
      if(modoItems && s.items_programados){
        asignacionTxt = '<div style="font-size:0.78em;color:#555;font-weight:600;margin-bottom:3px;">3 items a contar:</div>';
        s.items_programados.forEach(function(it){
          asignacionTxt += '<div style="font-size:0.8em;font-family:monospace;color:#1e293b;">• '+it.codigo_mp+' — '+it.nombre+'</div>';
        });
      } else {
        asignacionTxt = s.estanteria;
      }
      html += '<tr style="border-bottom:1px solid #e0ece9;'+bg+'">'
            + '<td style="padding:7px 12px;vertical-align:top;">'+semLabel+'</td>'
            + '<td style="padding:7px 12px;vertical-align:top;">'+s.lunes+'</td>'
            + '<td style="padding:7px 12px;font-weight:600;">'+asignacionTxt+'</td>'
            + '<td style="padding:7px 12px;text-align:center;vertical-align:top;">'+badge+'</td>'
            + '<td style="padding:7px 12px;text-align:center;vertical-align:top;">'+accion+'</td>'
            + '</tr>';
    });
    var resumen;
    if(modoItems){
      resumen = 'Tipo: <strong>'+d.tipo_material+'</strong> · Total &iacute;tems: '+d.total_items+
                ' · 3 items por semana · Ciclo completo en ~'+Math.ceil(d.total_items/3)+' semanas';
    } else {
      // Modo legacy MP: aclarar al usuario que solo cubre Materias Primas
      // físicas. Para Envase/Empaque hay que cambiar el filtro arriba.
      var hint = (!_conteoTipoFiltro || _conteoTipoFiltro === 'MP')
        ? ' · <span style="color:#1f5f5b;">Solo Materias Primas. Para Envase Primario/Secundario o Empaque cambia el filtro arriba.</span>'
        : '';
      resumen = 'Total estanter&iacute;as en rotaci&oacute;n: '+d.total_estanterias+
                ' &mdash; ciclo completo cada '+d.total_estanterias+' semanas' + hint;
    }
    html += '<tr style="background:#f5f5f5;font-size:0.8em;color:#888;"><td colspan="5" style="padding:6px 12px;">'+resumen+'</td></tr>';
    tbody.innerHTML = html;
  }catch(e){
    var tbody = document.getElementById('cnt-prog-rows');
    if(tbody) tbody.innerHTML = '<tr><td colspan="5" style="color:#c00;padding:10px;">Error cargando programaci&oacute;n: '+(e.message||e)+'</td></tr>';
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

// Event delegation: botones editar proveedor / eliminar lote dentro del
// conteo ciclico. Reusan los modales de Stock por Lote (mismo patron) —
// se construye un objeto compatible y se pushea a _lotes para que los
// handlers existentes lo encuentren por indice.
document.addEventListener('click', function(e){
  var btnProv = e.target.closest && e.target.closest('.cnt-prov-edit');
  var btnDel = e.target.closest && e.target.closest('.cnt-del-lote');
  if (!btnProv && !btnDel) return;
  var idx = parseInt((btnProv||btnDel).getAttribute('data-idx'),10);
  if (isNaN(idx) || !_conteoItems || !_conteoItems[idx]) return;
  var ci = _conteoItems[idx];
  // Adaptar al formato que esperan los modales existentes (mismo shape de /api/lotes)
  var fakeIdx = _lotes.push({
    material_id: ci.codigo_mp,
    material_nombre: ci.nombre,
    nombre_inci: ci.inci || '',
    proveedor: ci.proveedor || '',
    lote: ci.lote || '',
    cantidad_g: ci.stock_sistema,
    fecha_vencimiento: ci.fecha_vencimiento || '',
    stock_min_g: 0,
  }) - 1;
  if (btnProv) {
    abrirEditarProveedor(fakeIdx);
  } else {
    abrirEliminarLote(fakeIdx);
  }
});

async function cargarItemsConteo(est){
  try{
    var url = '/api/conteo/materiales?estanteria='+encodeURIComponent(est);
    if(_conteoTipoFiltro){
      url += '&tipo_material=' + encodeURIComponent(_conteoTipoFiltro);
    }
    var r = await fetch(url);
    _conteoItems = await r.json();
    var causas = ['Error de conteo','Consumo no descargado','Ingreso no registrado','Error unidad de medida','Merma justificada','Traslado no registrado','Material no identificado','Otro'];
    var causaOpts = causas.map(function(c){return '<option>'+c+'</option>';}).join('');
    // Color por tipo_material para diferenciar visualmente
    var tipoColor = {'MP':'#666','Envase Primario':'#0a66c2','Envase Secundario':'#2980b9','Empaque':'#7c3aed'};
    var h = '';
    _conteoItems.forEach(function(mp, i){
      var tipo = mp.tipo_material || 'MP';
      var col = tipoColor[tipo] || '#666';
      var lote = mp.lote || '';
      var prov = mp.proveedor || '';
      var loteSeg = lote || '_SIN_LOTE_';
      // Wrap row en index para que los handlers _conteoItems[i] sigan funcionando.
      h += '<tr id="cnt-row-'+i+'" data-cod="'+mp.codigo_mp+'" data-lote="'+lote+'">';
      h += '<td style="font-family:monospace;font-size:0.82em;">'+mp.codigo_mp+'<br><span style="font-size:0.7em;color:'+col+';font-weight:700;text-transform:uppercase;letter-spacing:0.4px;">'+tipo+'</span></td>';
      h += '<td style="font-size:0.85em;">'+mp.nombre+(mp.inci?'<br><span style="font-size:0.72em;color:#888;">'+mp.inci+'</span>':'')+'</td>';
      var loteTxt = lote ? '<span style="font-family:monospace;font-size:0.82em;">'+lote+'</span>' : '<span style="color:#bbb;font-style:italic;font-size:0.78em;">— sin lote —</span>';
      var posTxt = mp.posicion ? '<br><span style="font-size:0.72em;color:#888;">Pos: '+mp.posicion+'</span>' : '';
      var venTxt = mp.fecha_vencimiento ? '<br><span style="font-size:0.72em;color:#888;">Vence: '+mp.fecha_vencimiento.substr(0,10)+'</span>' : '';
      h += '<td>'+loteTxt+posTxt+venTxt+'</td>';
      // Proveedor con boton editar (reusa modal y datalist global del flujo Stock por Lote)
      var provHtml = prov ? prov : '<span style="color:#bbb;font-style:italic;font-size:0.78em;">— sin proveedor —</span>';
      h += '<td class="cnt-prov-cell" data-idx="'+i+'" style="font-size:0.82em;color:#475569;">'+provHtml+' <button class="cnt-prov-edit" data-idx="'+i+'" title="Editar proveedor del lote" style="margin-left:3px;padding:1px 5px;font-size:0.72em;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;border-radius:4px;cursor:pointer;">&#9999;&#65039;</button></td>';
      h += '<td style="text-align:right;font-weight:600;font-family:monospace;">'+Number(mp.stock_sistema).toLocaleString()+'</td>';
      h += '<td><input type="number" id="cnt-fis-'+i+'" min="0" step="0.1" oninput="calcDiff('+i+','+mp.stock_sistema+','+mp.precio_ref+')" style="width:120px;padding:6px;border:1px solid #dde;border-radius:6px;text-align:right;font-family:monospace;"></td>';
      h += '<td id="cnt-diff-'+i+'" style="text-align:right;font-family:monospace;font-weight:700;">--</td>';
      h += '<td id="cnt-pct-'+i+'" style="font-size:0.85em;">--</td>';
      h += '<td><select id="cnt-causa-'+i+'" style="width:140px;padding:5px;border:1px solid #dde;border-radius:6px;font-size:0.8em;"><option value="">Sin diferencia</option>'+causaOpts+'</select></td>';
      // Acciones: eliminar lote (con motivo) — reusa modal-eliminar-lote
      h += '<td style="text-align:center;"><button class="cnt-del-lote" data-idx="'+i+'" title="Eliminar lote (motivo obligatorio)" style="padding:3px 8px;font-size:0.75em;background:#c0392b;color:#fff;border-radius:4px;cursor:pointer;">&#128465;</button></td>';
      h += '</tr>';
    });
    document.getElementById('cnt-tbody').innerHTML = h || '<tr><td colspan="10" style="text-align:center;color:#999;">Sin materiales en esta estanteria con el filtro seleccionado</td></tr>';
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
      lote: mp.lote || '',
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
    var search = (document.getElementById('mee-search-input')||{}).value || '';
    var items = d.items || [];
    if(search){
      var q = search.toLowerCase();
      items = items.filter(function(m){
        return (m.descripcion||'').toLowerCase().indexOf(q)>=0 ||
               (m.codigo||'').toLowerCase().indexOf(q)>=0 ||
               (m.proveedor||'').toLowerCase().indexOf(q)>=0;
      });
    }
    window._meeItems = items;  // cache para vista agrupada
    if(!items.length){
      tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;">Sin items activos</td></tr>'; return;
    }
    var aC={critico:'#e74c3c',bajo:'#e67e22',advertencia:'#f39c12',ok:'#27ae60',sin_minimo:'#95a5a6'};
    var aL={critico:'&#9940; Critico',bajo:'&#9888; Bajo',advertencia:'&#128993; Alerta',ok:'&#10003; OK',sin_minimo:'—'};
    var h='';
    items.forEach(function(m){
      var c=aC[m.alerta]||'#95a5a6';
      var lbl=aL[m.alerta]||'';
      var ob=m.obsoleto?' <span style="background:#ffc107;color:#856404;border-radius:3px;padding:1px 5px;font-size:0.75em;">+90d</span>':'';
      h+='<tr data-cod="'+_escHTML(m.codigo)+'">';
      h+='<td style="font-family:monospace;font-size:0.78em;color:#555;">'+_escHTML(m.codigo)+'</td>';
      h+='<td style="font-size:0.88em;">'+_escHTML(m.descripcion)+ob+'</td>';
      h+='<td style="font-size:0.8em;color:#777;">'+_escHTML(m.categoria||'')+'</td>';
      h+='<td style="font-weight:700;">'+m.stock_actual+' <span style="color:#999;font-size:0.8em;">'+_escHTML(m.unidad||'und')+'</span></td>';
      h+='<td style="color:#aaa;font-size:0.88em;">'+(m.stock_minimo||'—')+'</td>';
      h+='<td><span style="color:'+c+';font-weight:600;font-size:0.82em;">'+lbl+'</span></td>';
      h+='<td style="font-size:0.78em;color:#666;max-width:120px;overflow:hidden;text-overflow:ellipsis">'+_escHTML(m.proveedor||'-')+'</td>';
      h+='<td style="white-space:nowrap">';
      h+='<button onclick="meeAjustar(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Ajustar stock" style="padding:4px 7px;border:none;background:#0891b2;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;margin-right:2px">&#9878;</button>';
      h+='<button onclick="meeProveedor(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Cambiar proveedor" style="padding:4px 7px;border:none;background:#6d28d9;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;margin-right:2px">&#127981;</button>';
      h+='<button onclick="meeMin(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;,'+(m.stock_minimo||0)+')" title="Stock mínimo" style="padding:4px 7px;border:none;background:#d97706;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;margin-right:2px">&#128208;</button>';
      h+='<button onclick="meeHistorico(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Histórico de movimientos" style="padding:4px 7px;border:none;background:#15803d;color:#fff;border-radius:4px;cursor:pointer;font-size:11px;margin-right:2px">&#128202;</button>';
      h+='<button onclick="meeArchivar(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)" title="Archivar (eliminar)" style="padding:4px 7px;border:none;background:#dc2626;color:#fff;border-radius:4px;cursor:pointer;font-size:11px">&#128465;</button>';
      h+='</td>';
      h+='</tr>';
    });
    tb.innerHTML=h;
    if(window._meeAgrupado) renderMeeAgrupado();
  }catch(e){ console.error('cargarMeeStock:',e); }
}

// ─── Acciones MEE (paridad con MP) ──────────────────────────────
async function meeAjustar(codigo){
  var nuevo = prompt('Nueva cantidad de stock para '+codigo+':');
  if(nuevo===null) return;
  var n = parseFloat(nuevo);
  if(isNaN(n) || n<0){ alert('Cantidad inválida'); return; }
  var motivo = prompt('Motivo del ajuste (obligatorio):');
  if(!motivo){ alert('Motivo requerido'); return; }
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/ajustar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cantidad_nueva: n, motivo: motivo})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast('Stock ajustado: '+d.stock_anterior+' → '+d.stock_nuevo, 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeProveedor(codigo){
  var prov = prompt('Proveedor para '+codigo+' (vacío para limpiar):', '');
  if(prov===null) return;
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/proveedor', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({proveedor: prov.trim()})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Proveedor actualizado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeMin(codigo, actual){
  var n = prompt('Nuevo stock mínimo para '+codigo+' (actual: '+actual+'):', actual);
  if(n===null) return;
  var num = parseFloat(n); if(isNaN(num) || num<0){ alert('Inválido'); return; }
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/stock-minimo', {
      method:'PUT', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stock_minimo: num})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Mínimo actualizado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeHistorico(codigo){
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo)+'/historico');
    var d = await r.json();
    var movs = d.movimientos || [];
    var html = '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px" id="mee-hist-modal" onclick="if(event.target===this)this.remove()">'+
      '<div style="background:#fff;border-radius:14px;padding:20px;width:800px;max-width:100%;max-height:90vh;overflow-y:auto" onclick="event.stopPropagation()">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">'+
          '<h3 style="margin:0">📊 Histórico · '+_escHTML(codigo)+'</h3>'+
          '<button onclick="document.getElementById(&quot;mee-hist-modal&quot;).remove()" style="background:transparent;border:1px solid #d6d3d1;border-radius:6px;width:32px;height:32px;cursor:pointer;font-size:16px">&#10005;</button>'+
        '</div>'+
        (movs.length ?
          '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Fecha</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Tipo</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:right;font-size:11px;text-transform:uppercase">Cantidad</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Lote/Batch</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Responsable</th>'+
            '<th style="background:#fafaf9;padding:8px;text-align:left;font-size:11px;text-transform:uppercase">Observaciones</th>'+
          '</tr></thead><tbody>'+
          movs.map(function(m){
            var tCol = m.tipo==='Entrada'?'#16a34a':m.tipo==='Salida'?'#dc2626':'#7c3aed';
            return '<tr style="border-bottom:1px solid #f5f5f4'+(m.anulado?';opacity:0.5;text-decoration:line-through':'')+'">'+
              '<td style="padding:7px;font-size:12px">'+_escHTML((m.fecha||'').substring(0,16))+'</td>'+
              '<td style="padding:7px"><span style="background:'+tCol+'22;color:'+tCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_escHTML(m.tipo)+'</span></td>'+
              '<td style="padding:7px;text-align:right;font-weight:700">'+m.cantidad+' '+_escHTML(m.unidad||'und')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666">'+_escHTML(m.lote_ref||m.batch_ref||'-')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666">'+_escHTML(m.responsable||'-')+'</td>'+
              '<td style="padding:7px;font-size:11px;color:#666;max-width:300px;word-wrap:break-word">'+_escHTML(m.observaciones||'')+'</td>'+
            '</tr>';
          }).join('')+
          '</tbody></table>'
          : '<div style="text-align:center;color:#a8a29e;padding:40px">Sin movimientos registrados</div>')+
      '</div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
  } catch(e){ alert('Error: '+e.message); }
}

async function meeArchivar(codigo){
  if(!confirm('¿Archivar (eliminar de la lista) "'+codigo+'"? Los movimientos históricos se conservan.')) return;
  try {
    var r = await fetch('/api/mee/'+encodeURIComponent(codigo), {method:'DELETE'});
    if(!r.ok){ alert('Error'); return; }
    _toast(codigo+' archivado', 1);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

async function meeImportarExcel(){
  if(!confirm('Importar inventario MEE desde el Excel cargado?\\n\\n68 items en 5 categorías (Envases, Goteros, Tapas, Etiquetas, Plegadizas).\\n\\nLos códigos existentes se actualizan, los nuevos se crean.')) return;
  try {
    // Cargar JSON desde el repo
    var rJson = await fetch('/static/scripts/mee_excel_import.json');
    if(!rJson.ok){
      // Fallback: pedir URL manual
      alert('No se encuentra scripts/mee_excel_import.json. Asegúrate de hacer deploy.');
      return;
    }
    var items = await rJson.json();
    var r = await fetch('/api/mee/import-bulk', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({items: items, modo: 'upsert'})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    alert('✅ Importación completa\\n\\nInsertados: '+d.insertados+'\\nActualizados: '+d.actualizados+'\\nTotal: '+d.total_recibidos);
    cargarMeeStock();
  } catch(e){ alert('Error: '+e.message); }
}

function meeAgrupadoToggle(){
  window._meeAgrupado = !window._meeAgrupado;
  var tabla = document.getElementById('mee-tabla-estandar');
  var wrap = document.getElementById('mee-agrupado-wrap');
  var btn = document.getElementById('mee-agrupado-btn');
  if(window._meeAgrupado){
    tabla.style.display = 'none';
    wrap.style.display = 'block';
    btn.innerHTML = '📋 Lista plana';
    renderMeeAgrupado();
  } else {
    tabla.style.display = '';
    wrap.style.display = 'none';
    btn.innerHTML = '📑 Agrupado';
  }
}

function renderMeeAgrupado(){
  var wrap = document.getElementById('mee-agrupado-wrap');
  var items = window._meeItems || [];
  // Agrupar por categoria
  var grupos = {};
  items.forEach(function(m){
    var cat = m.categoria || 'Sin categoría';
    if(!grupos[cat]) grupos[cat] = [];
    grupos[cat].push(m);
  });
  var cats = Object.keys(grupos).sort();
  var aC={critico:'#e74c3c',bajo:'#e67e22',advertencia:'#f39c12',ok:'#27ae60',sin_minimo:'#95a5a6'};
  wrap.innerHTML = cats.map(function(cat){
    var grupo = grupos[cat];
    var totalStock = grupo.reduce(function(a,m){return a+(m.stock_actual||0)},0);
    var nBajo = grupo.filter(function(m){return m.alerta==='critico'||m.alerta==='bajo'}).length;
    return '<details style="margin-bottom:10px;background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 16px" open>'+
      '<summary style="cursor:pointer;font-weight:700;color:#1c1917;display:flex;align-items:center;gap:10px;list-style:none">'+
        '<span style="font-size:15px">📦 '+_escHTML(cat)+'</span>'+
        '<span style="font-size:12px;color:#78716c;font-weight:500">'+grupo.length+' items · '+totalStock.toLocaleString('es-CO')+' und total'+
          (nBajo>0?' · <span style="color:#dc2626;font-weight:700">'+nBajo+' bajo mínimo</span>':'')+'</span>'+
      '</summary>'+
      '<div style="margin-top:10px;display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px">'+
        grupo.map(function(m){
          var col = aC[m.alerta]||'#27ae60';
          return '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-left:3px solid '+col+';border-radius:8px;padding:10px;cursor:pointer" onclick="meeHistorico(&quot;'+_escHTML(m.codigo).replace(/"/g,'&quot;')+'&quot;)">'+
            '<div style="font-weight:600;font-size:12px;color:#1c1917">'+_escHTML(m.descripcion)+'</div>'+
            '<div style="font-size:10px;color:#78716c;margin-top:2px;font-family:monospace">'+_escHTML(m.codigo)+'</div>'+
            '<div style="display:flex;justify-content:space-between;margin-top:6px;align-items:center">'+
              '<span style="font-weight:700;font-size:14px;color:#1c1917">'+(m.stock_actual||0).toLocaleString('es-CO')+' '+_escHTML(m.unidad||'und')+'</span>'+
              '<span style="font-size:10px;color:#999">min '+(m.stock_minimo||0)+'</span>'+
            '</div>'+
          '</div>';
        }).join('')+
      '</div>'+
    '</details>';
  }).join('');
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
var _meeAcondItems=[];
function cargarMeeParaAcond(){
  fetch("/api/mee/stock").then(function(r){return r.json();}).then(function(d){
    _meeAcondItems=(d.items||[]).filter(function(m){return m.stock_actual>0;});
  }).catch(function(){});
}
function addMEERowAcond(){
  var cont=document.getElementById("ac-mee-rows");
  var msg=document.getElementById("ac-mee-msg"); if(msg) msg.style.display="none";
  var row=document.createElement("div");
  row.style.cssText="display:flex;gap:8px;align-items:center;";
  var selHtml='<select style="flex:2;padding:5px;border:1px solid #ccc;border-radius:4px;font-size:12px;">'+
    '<option value="">-- Seleccionar MEE --</option>';
  _meeAcondItems.forEach(function(m){
    selHtml+='<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' (stock:'+m.stock_actual+')</option>';
  });
  selHtml+='</select>';
  row.innerHTML=selHtml+
    '<input type="number" min="1" placeholder="Cant" style="flex:1;padding:5px;border:1px solid #ccc;border-radius:4px;font-size:12px;">'+
    '<button onclick="this.parentElement.remove();_checkMEEMsg();" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:12px;">&times;</button>';
  cont.appendChild(row);
}
function _checkMEEMsg(){
  var cont=document.getElementById("ac-mee-rows");
  var msg=document.getElementById("ac-mee-msg");
  if(msg) msg.style.display=(cont&&cont.children.length===0)?"block":"none";
}
var _envPresCount=0,_envMEE=[];
async function cargarEnvasadoTab(){
  var sel=document.getElementById('env-prod-sel');if(!sel) return;
  // Only reload if selector is empty or has just the placeholder
  var needsLoad=(sel.options.length<=1);
  if(needsLoad) sel.innerHTML='<option value="">Cargando producciones...</option>';
  try{
    var rp=await fetch('/api/produccion');var dp=await rp.json();
    var rm=await fetch('/api/mee');var dm=await rm.json();
    var prods=(dp.producciones||[]).filter(function(p){return p.estado==='Completado';});
    _envMEE=dm.items||[];
    // Only rebuild if we got real data
    if(prods.length>0){
      sel.innerHTML='<option value="">-- Selecciona produccion terminada --</option>';
      prods.forEach(function(p){
        var op=document.createElement('option');
        op.value=p.id;
        op.dataset.producto=p.producto||'';
        op.dataset.lote=p.lote||('PROD-'+String(p.id).padStart(5,'0'));
        op.dataset.batch=p.cantidad||0;
        op.text=(p.lote||'PROD-'+String(p.id).padStart(5,'0'))+' - '+(p.producto||'?')+' ('+p.cantidad+'kg) '+(p.fecha||'').slice(0,10);
        sel.appendChild(op);
      });
    }
  }catch(e){if(needsLoad) sel.innerHTML='<option value="">Error - recarga la pagina</option>';}
  await cargarHistEnvasado();
  if(!document.getElementById('env-pres-rows').children.length){
    _envPresCount=0;addEnvPres();
  }
}
function cargarDatosProduccion(){
  var sel=document.getElementById('env-prod-sel');if(!sel) return;
  var opt=sel.options[sel.selectedIndex];if(!opt||!opt.value) return;
  var p=document.getElementById('env-producto');var l=document.getElementById('env-lote');var b=document.getElementById('env-batch-total');
  if(p) p.value=opt.dataset.producto||'';
  if(l) l.value=opt.dataset.lote||'';
  if(b) b.value=(parseFloat(opt.dataset.batch||0)*1000).toFixed(0)+' g';
}
function addEnvPres(){
  if(_envPresCount>=2){alert('Maximo 2 presentaciones');return;}
  _envPresCount++;var n=_envPresCount;
  var cats=['Envase','Frasco','Gotero'];
  var optEnv=_envMEE.filter(function(m){return cats.indexOf(m.categoria)>=0;}).map(function(m){return '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' ('+m.stock_actual+')</option>';}).join('');
  var optTap=_envMEE.filter(function(m){return m.categoria==='Tapa';}).map(function(m){return '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' ('+m.stock_actual+')</option>';}).join('');
  var div=document.createElement('div');div.id='env-pres-'+n;div.style.cssText='background:#fff;border:1px solid #ddd;border-radius:6px;padding:12px;margin-bottom:8px;';
  div.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><strong style="font-size:13px;color:#1a4a7a">Presentacion '+n+'</strong>'+(n>1?'<button onclick="rmEnvPres('+n+')" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px">Quitar</button>':'')+'</div><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;"><div><label style="font-size:11px">Presentacion</label><input id="ep'+n+'-pres" placeholder="Ej: 30ml" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div><div><label style="font-size:11px">Envase</label><select id="ep'+n+'-env" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:11px;"><option value="">--</option>'+optEnv+'</select></div><div><label style="font-size:11px">Tapa</label><select id="ep'+n+'-tap" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;font-size:11px;"><option value="">--</option>'+optTap+'</select></div><div><label style="font-size:11px">Unidades</label><input id="ep'+n+'-uds" type="number" min="1" placeholder="0" style="width:100%;padding:6px;border:1px solid #ccc;border-radius:4px;box-sizing:border-box;"></div></div>';
  document.getElementById('env-pres-rows').appendChild(div);
  if(_envPresCount>=2){var btn=document.getElementById('env-add-pres-btn');if(btn)btn.style.display='none';}
}
function rmEnvPres(n){var el=document.getElementById('env-pres-'+n);if(el)el.remove();_envPresCount--;var btn=document.getElementById('env-add-pres-btn');if(btn)btn.style.display='';}
async function registrarEnvasado(){
  var prodSel=document.getElementById('env-prod-sel');
  if(!prodSel||!prodSel.value){alert('Selecciona un batch de produccion');return;}
  var prodId=parseInt(prodSel.value);
  var lote=(document.getElementById('env-lote')||{value:''}).value.trim();
  var producto=(document.getElementById('env-producto')||{value:''}).value.trim();
  var obs=(document.getElementById('env-obs')||{value:''}).value.trim();
  var presentaciones=[];
  for(var i=1;i<=2;i++){
    var presEl=document.getElementById('ep'+i+'-pres');if(!presEl) continue;
    var pres=presEl.value.trim();
    var envCod=(document.getElementById('ep'+i+'-env')||{value:''}).value;
    var tapCod=(document.getElementById('ep'+i+'-tap')||{value:''}).value;
    var uds=parseInt((document.getElementById('ep'+i+'-uds')||{value:0}).value||0);
    if(!pres||uds<=0) continue;
    presentaciones.push({presentacion:pres,envase_codigo:envCod,tapa_codigo:tapCod,unidades:uds});
  }
  if(!presentaciones.length){alert('Agrega al menos una presentacion con unidades');return;}
  var msg=document.getElementById('env-msg');
  if(msg) msg.innerHTML='<span style="color:#666;">Registrando...</span>';
  var allAlertas=[];
  for(var j=0;j<presentaciones.length;j++){
    var p=presentaciones[j];
    try{
      var r=await fetch('/api/envasado',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({produccion_id:prodId,lote:lote,producto:producto,presentacion:p.presentacion,unidades:p.unidades,envase_codigo:p.envase_codigo,tapa_codigo:p.tapa_codigo,operador:OPER_ACTUAL||'Operario',observaciones:obs})});
      var d=await r.json();
      if(!r.ok){if(msg)msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>';return;}
      if(d.alertas_mee) allAlertas=allAlertas.concat(d.alertas_mee);
    }catch(e){if(msg)msg.innerHTML='<div style="color:#dc3545;">Error: '+e.message+'</div>';return;}
  }
  var alertTxt=allAlertas.length?' | MEE bajo minimo: '+allAlertas.map(function(a){return a.nombre+' deficit '+a.deficit;}).join(', ')+'. Solicitud enviada a Compras.':'';
  if(msg) msg.innerHTML='<div style="color:#28a745;padding:8px;background:#d4edda;border-radius:4px;">Envasado registrado. MEE descontado.'+alertTxt+'</div>';
  await cargarHistEnvasado();
  if(typeof loadAlertasMEE==='function') setTimeout(loadAlertasMEE,500);
}
async function cargarHistEnvasado(){
  var tb=document.getElementById('env-tbody');if(!tb) return;
  try{
    var r=await fetch('/api/envasado');var d=await r.json();var rows=d.envasados||[];
    if(!rows.length){tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;padding:12px;">Sin registros</td></tr>';return;}
    tb.innerHTML=rows.map(function(e){return '<tr style="border-bottom:1px solid #eee;"><td style="padding:6px;font-family:monospace;font-size:12px;">'+e.lote+'</td><td style="padding:6px;">'+e.producto+'</td><td style="padding:6px;">'+e.presentacion+'</td><td style="padding:6px;text-align:center;">'+e.unidades+'</td><td style="padding:6px;font-size:11px;color:#666;">'+e.envase_codigo+'</td><td style="padding:6px;font-size:11px;color:#666;">'+e.tapa_codigo+'</td><td style="padding:6px;font-size:12px;">'+e.fecha+'</td><td style="padding:6px;font-size:12px;">'+e.operador+'</td></tr>';}).join('');
  }catch(e){if(tb)tb.innerHTML='<tr><td colspan="8">Error</td></tr>';}
}
async function cargarEnvasadosPendientes(){
  var sel=document.getElementById('ac-envasado-sel');if(!sel) return;
  try{
    var r=await fetch('/api/envasado/pendientes-acond');var d=await r.json();var pend=d.pendientes||[];
    sel.innerHTML='<option value="">-- Selecciona batch envasado listo --</option>';
    pend.forEach(function(e){var op=document.createElement('option');op.value=e.id;op.dataset.lote=e.lote||'';op.dataset.producto=e.producto||'';op.dataset.pres=e.presentacion||'';op.dataset.uds=e.unidades||0;op.dataset.batch=e.batch_g||0;op.text=e.lote+' - '+e.producto+' '+e.presentacion+' ('+e.unidades+' uds) '+e.fecha;sel.appendChild(op);});
  }catch(e){}
}
function cargarDesdeEnvasado(){
  var sel=document.getElementById('ac-envasado-sel');if(!sel||!sel.value) return;
  var opt=sel.options[sel.selectedIndex];
  var f=function(id,v){var el=document.getElementById(id);if(el)el.value=v;};
  f('ac-envasado-id',opt.value);f('ac-lote',opt.dataset.lote||'');f('ac-prod',opt.dataset.producto||'');
  f('ac-pres',opt.dataset.pres||'');f('ac-uds',opt.dataset.uds||'');f('ac-batch',opt.dataset.batch||'');
}

function registrarAcond(){
  var lote=document.getElementById("ac-lote").value;
  var prod=document.getElementById("ac-prod").value;
  if(!lote||!prod){_toast("Lote y producto son obligatorios",0);return;}
  var meeRows=document.getElementById("ac-mee-rows").querySelectorAll("div");
  var mee_consumido=[];
  var meeOk=true;
  meeRows.forEach(function(row){
    var sel=row.querySelector("select");
    var qty=row.querySelector("input[type=number]");
    if(sel&&qty&&sel.value){
      var c=parseInt(qty.value)||0;
      if(c<=0){meeOk=false;return;}
      mee_consumido.push({codigo:sel.value,cantidad:c});
    }
  });
  if(!meeOk){_toast("Verifica cantidades MEE (deben ser > 0)",0);return;}
  var d={
    lote:lote,
    producto:prod,
    presentacion:document.getElementById("ac-pres").value,
    cantidad_batch_g:parseFloat(document.getElementById("ac-batch").value)||0,
    unidades_producidas:parseInt(document.getElementById("ac-uds").value)||0,
    fecha:document.getElementById("ac-fecha").value,
    observaciones:document.getElementById("ac-obs").value,
    sku:document.getElementById("ac-sku").value.trim(),
    precio_base:parseFloat(document.getElementById("ac-precio").value)||0,
    mee_consumido:mee_consumido
  };
  var msgEl=document.getElementById("ac-form-msg");
  fetch("/api/acondicionamiento",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
  .then(function(r){return r.json();})
  .then(function(j){
    if(j.ok||j.id){
      var info="\u2705 Batch registrado #"+j.id;
      if(mee_consumido.length) info+=" | MEE descontado: "+mee_consumido.length+" item(s)";
      _toast(info,1);
      ["ac-lote","ac-prod","ac-pres","ac-batch","ac-uds","ac-obs","ac-sku","ac-precio"].forEach(function(id){document.getElementById(id).value="";});
      document.getElementById("ac-mee-rows").innerHTML="";
      _checkMEEMsg();
      if(msgEl) msgEl.innerHTML="";
      loadAcond();
    } else {
      var err="Error: "+(j.error||"desconocido");
      _toast(err,0);
      if(msgEl) msgEl.innerHTML='<span style="color:red;">'+err+'</span>';
    }
  }).catch(function(e){
    _toast("Error de red: "+e,0);
    if(msgEl) msgEl.innerHTML='<span style="color:red;">Error de red: '+e+'</span>';
  });
}
function loadColaSinEnvasar(){
  var tb=document.getElementById('cola-env-tbody');
  if(!tb)return;
  tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/producciones/sin-envasar')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows=d.cola||[];
      if(!rows.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de envasar</td></tr>';return;}
      _sinEnvasarMap={};
      rows.forEach(function(r){_sinEnvasarMap[r.id]=r;});
      tb.innerHTML=rows.map(function(r){
        return '<tr style="border-bottom:1px solid #c8e6c9">'+
          '<td style="padding:7px;font-weight:600">'+(r.lote||'S/L')+'</td>'+
          '<td style="padding:7px">'+r.producto+'</td>'+
          '<td style="padding:7px;text-align:center">'+(r.cantidad_kg||0)+' kg</td>'+
          '<td style="padding:7px">'+(r.fecha||'')+'</td>'+
          '<td style="padding:7px">'+(r.operador||'')+'</td>'+
          '<td style="padding:7px"><button onclick="abrirEnvasado('+r.id+')" '+
          'style="background:#1b5e20;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">'+
          '&#128230; Envasar</button></td>'+
          '</tr>';
      }).join('');
    })
    .catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>';});
}
var _envActObj = null;
var _sinEnvasarMap = {};
var _pendAcondMap  = {};
function _buildMeeOpts(selectedVal){
  var envCats=['Envase','Frasco','Gotero','Tarro'];
  var eOpts='<option value="">-- Sin envase --</option>';
  var tOpts='<option value="">-- Sin tapa --</option>';
  (_envSimpleMEE||[]).forEach(function(m){
    var opt='<option value="'+m.codigo+'"'+(m.codigo===selectedVal?' selected':'')+'>'
      +m.codigo+' - '+m.descripcion+' ('+m.stock_actual+')</option>';
    if(envCats.indexOf(m.categoria)>=0) eOpts+=opt;
    else if(m.categoria==='Tapa') tOpts+=opt;
  });
  return {env:eOpts, tap:tOpts};
}
function _presRowHtml(idx){
  var opts=_buildMeeOpts('');
  return '<div class="pres-row" id="pr-'+idx+'" style="background:#f0f4f8;border-radius:8px;padding:12px;margin-bottom:10px;position:relative">'
    +'<div style="display:grid;grid-template-columns:2fr 2fr 2fr 1fr;gap:10px;align-items:end">'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Presentacion *</label>'
    +'<input type="text" class="pr-pres" placeholder="Ej: Frasco 30ml" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Envase (MEE)</label>'
    +'<select class="pr-env" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px">'+opts.env+'</select></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Tapa (MEE)</label>'
    +'<select class="pr-tap" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px">'+opts.tap+'</select></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Unidades *</label>'
    +'<input type="number" class="pr-uds" min="1" placeholder="66" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'</div>'
    +(idx>0?'<button onclick="removePresRow('+idx+')" style="position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:12px;cursor:pointer">&#10005;</button>':'')
    +'</div>';
}
var _prIdx=0;
function abrirEnvasado(id){
  var lote_obj=_sinEnvasarMap[id]||{};
  _envActObj=lote_obj;
  _prIdx=0;
  document.getElementById('env-act-prod').textContent=lote_obj.producto||'';
  document.getElementById('env-act-prod-raw').value=lote_obj.producto||'';
  document.getElementById('env-act-lote').textContent=lote_obj.lote||'S/L';
  document.getElementById('env-act-batch').textContent=(lote_obj.cantidad_kg||0)+' kg';
  document.getElementById('env-act-prod-id').value=lote_obj.id||'';
  var rows=document.getElementById('env-pres-rows');
  rows.innerHTML=_presRowHtml(_prIdx);
  document.getElementById('env-act-msg').innerHTML='';
  document.getElementById('env-panel-activo').style.display='block';
  document.getElementById('env-panel-activo').scrollIntoView({behavior:'smooth',block:'start'});
}
function addPresRow(){
  _prIdx++;
  document.getElementById('env-pres-rows').insertAdjacentHTML('beforeend',_presRowHtml(_prIdx));
}
function removePresRow(idx){
  var el=document.getElementById('pr-'+idx);if(el)el.remove();
}
function cerrarEnvActivo(){
  _envActObj=null;
  document.getElementById('env-panel-activo').style.display='none';
  document.getElementById('env-pres-rows').innerHTML='';
}
async function registrarEnvasadoMulti(){
  if(!_envActObj){return;}
  var rows=document.querySelectorAll('#env-pres-rows .pres-row');
  if(!rows.length){_toast('Agrega al menos una presentacion',0);return;}
  var payload=[];
  var ok=true;
  rows.forEach(function(row){
    var pres=(row.querySelector('.pr-pres')||{value:''}).value.trim();
    var uds=parseInt((row.querySelector('.pr-uds')||{value:0}).value||0);
    var env=(row.querySelector('.pr-env')||{value:''}).value;
    var tap=(row.querySelector('.pr-tap')||{value:''}).value;
    if(!pres||uds<=0){ok=false;return;}
    payload.push({pres:pres,uds:uds,env:env,tap:tap});
  });
  if(!ok){_toast('Completa presentacion y unidades en todas las filas',0);return;}
  var msg=document.getElementById('env-act-msg');
  msg.innerHTML='<span style="color:#666">Registrando...</span>';
  var errores=[];
  for(var i=0;i<payload.length;i++){
    var p=payload[i];
    try{
      var r=await fetch('/api/envasado',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          produccion_id:_envActObj.id||null,
          lote:_envActObj.lote||'',
          producto:_envActObj.producto||'',
          presentacion:p.pres,
          unidades:p.uds,
          envase_codigo:p.env||'',
          tapa_codigo:p.tap||'',
          operador:OPER_ACTUAL||'Operario',
          batch_g:(_envActObj.cantidad_kg||0)*1000
        })
      });
      var d=await r.json();
      if(!r.ok&&!d.id){errores.push(p.pres+': '+(d.error||'error'));}
    }catch(e){errores.push(p.pres+': error de red');}
  }
  if(errores.length){
    msg.innerHTML='<span style="color:red">'+errores.join(' | ')+'</span>';
  }else{
    _toast('&#9989; Envasado registrado ('+payload.length+' presentacion'+(payload.length>1?'es':'')+')',1);
    cerrarEnvActivo();
    loadColaSinEnvasar();
    if(typeof cargarHistEnvasado==='function') cargarHistEnvasado();
  }
}
function loadColaAcond(){
  var tb=document.getElementById('cola-acond-tbody');
  if(!tb)return;
  tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#999;padding:10px">Cargando...</td></tr>';
  fetch('/api/envasado/pendientes-acond')
    .then(function(r){return r.json();})
    .then(function(d){
      var rows=d.pendientes||[];
      if(!rows.length){tb.innerHTML='<tr><td colspan="6" style="text-align:center;color:#27ae60;padding:10px">&#10003; Sin lotes pendientes de acondicionar</td></tr>';return;}
      _pendAcondMap={};
      rows.forEach(function(r){_pendAcondMap[r.id]=r;});
      tb.innerHTML=rows.map(function(r){
        return '<tr style="border-bottom:1px solid #bbdefb">'+
          '<td style="padding:7px;font-weight:600">'+(r.lote||'S/L')+'</td>'+
          '<td style="padding:7px">'+r.producto+'</td>'+
          '<td style="padding:7px;text-align:center">'+(r.unidades||0)+'</td>'+
          '<td style="padding:7px">'+(r.presentacion||'')+'</td>'+
          '<td style="padding:7px">'+(r.fecha||'')+'</td>'+
          '<td style="padding:7px"><button onclick="prefillAcond('+r.id+')" '+
          'style="background:#0d47a1;color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:12px;cursor:pointer">'+
          '&#128393; Acondicionar</button></td>'+
          '</tr>';
      }).join('');
    })
    .catch(function(){tb.innerHTML='<tr><td colspan="6" style="color:#c00;text-align:center">Error cargando cola</td></tr>';});
}
function prefillAcond(id){ abrirAcond(id); }
var _acActObj = null;
var _acPrIdx = 0;
function _acPresRowHtml(idx, pres, uds){
  pres = pres||''; uds = uds||'';
  return '<div class="ac-pres-row" id="acpr-'+idx+'" style="background:#f0f4f8;border-radius:8px;padding:12px;margin-bottom:10px;position:relative">'
    +'<div style="display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;align-items:end">'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Presentacion / SKU *</label>'
    +'<input type="text" class="acpr-pres" placeholder="Ej: LBHA-30ML" value="'+pres+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Unidades *</label>'
    +'<input type="number" class="acpr-uds" min="1" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Etiquetas</label>'
    +'<input type="number" class="acpr-et" min="0" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'<div><label style="font-size:12px;font-weight:600;color:#555;display:block;margin-bottom:3px">Plegadizas</label>'
    +'<input type="number" class="acpr-pl" min="0" placeholder="66" value="'+uds+'" style="width:100%;padding:8px;border:1px solid #ccc;border-radius:4px;font-size:13px"></div>'
    +'</div>'
    +(idx>0?'<button onclick="removeAcPresRow('+idx+')" style="position:absolute;top:8px;right:8px;background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:12px;cursor:pointer">&#10005;</button>':'')
    +'</div>';
}
function abrirAcond(id){
  var env=_pendAcondMap[id]||{};
  _acActObj = env;
  _acPrIdx = 0;
  document.getElementById('ac-act-prod').textContent = env.producto||'';
  document.getElementById('ac-act-prod-raw').value = env.producto||'';
  document.getElementById('ac-act-lote').textContent = env.lote||'S/L';
  document.getElementById('ac-act-lote-raw').value = env.lote||'';
  document.getElementById('ac-act-uds-info').textContent = (env.unidades||0)+' uds disponibles';
  document.getElementById('ac-act-env-id').value = env.id||'';
  var fEl=document.getElementById('ac-act-fecha'); if(fEl) fEl.value=new Date().toISOString().slice(0,10);
  var dEl=document.getElementById('ac-act-destino'); if(dEl) dEl.value='';
  var obsEl=document.getElementById('ac-act-obs'); if(obsEl) obsEl.value='';
  var msgEl=document.getElementById('ac-act-msg'); if(msgEl) msgEl.innerHTML='';
  var rows=document.getElementById('ac-pres-rows');
  if(rows) rows.innerHTML=_acPresRowHtml(0, env.presentacion||'', env.unidades||'');
  var fm=document.getElementById('ac-form-manual'); if(fm) fm.style.display='none';
  document.getElementById('ac-panel-activo').style.display='block';
  document.getElementById('ac-panel-activo').scrollIntoView({behavior:'smooth',block:'start'});
}
function addAcPresRow(){
  _acPrIdx++;
  document.getElementById('ac-pres-rows').insertAdjacentHTML('beforeend',_acPresRowHtml(_acPrIdx,'',''));
}
function removeAcPresRow(idx){
  var el=document.getElementById('acpr-'+idx); if(el) el.remove();
}
function cerrarAcondActivo(){
  _acActObj=null;
  document.getElementById('ac-panel-activo').style.display='none';
  var rows=document.getElementById('ac-pres-rows'); if(rows) rows.innerHTML='';
  var fm=document.getElementById('ac-form-manual'); if(fm) fm.style.display='block';
}
async function registrarAcondDesdePanel(){
  if(!_acActObj){ _toast('No hay lote activo',0); return; }
  var lote=(document.getElementById('ac-act-lote-raw')||{value:''}).value.trim();
  var producto=(document.getElementById('ac-act-prod-raw')||{value:''}).value.trim();
  var fecha=(document.getElementById('ac-act-fecha')||{value:''}).value;
  var destino=(document.getElementById('ac-act-destino')||{value:''}).value.trim();
  var obs=(document.getElementById('ac-act-obs')||{value:''}).value.trim();
  if(!lote||!producto){ _toast('Datos de lote incompletos',0); return; }
  var presRows=document.querySelectorAll('#ac-pres-rows .ac-pres-row');
  if(!presRows.length){ _toast('Agrega al menos una presentacion',0); return; }
  var payload=[];
  var ok=true;
  presRows.forEach(function(row){
    var pres=(row.querySelector('.acpr-pres')||{value:''}).value.trim();
    var uds=parseInt((row.querySelector('.acpr-uds')||{value:0}).value||0);
    var et=parseInt((row.querySelector('.acpr-et')||{value:0}).value||0);
    var pl=parseInt((row.querySelector('.acpr-pl')||{value:0}).value||0);
    if(!pres||uds<=0){ok=false;return;}
    payload.push({pres:pres,uds:uds,et:et,pl:pl});
  });
  if(!ok){ _toast('Completa presentacion y unidades en todas las filas',0); return; }
  var msgEl=document.getElementById('ac-act-msg');
  if(msgEl) msgEl.innerHTML='<span style="color:#666">Registrando...</span>';
  var errores=[];
  for(var i=0;i<payload.length;i++){
    var p=payload[i];
    var obsCompleto='Etiquetas: '+p.et+' | Plegadizas: '+p.pl+(destino?' | Destino: '+destino:'')+(obs?' | '+obs:'');
    try{
      var r=await fetch('/api/acondicionamiento',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          lote:lote, producto:producto,
          presentacion:p.pres,
          cantidad_batch_g:0,
          unidades_producidas:p.uds,
          fecha:fecha,
          observaciones:obsCompleto,
          sku:p.pres, precio_base:0, mee_consumido:[]
        })
      });
      var d=await r.json();
      if(!r.ok&&!d.id){ errores.push(p.pres+': '+(d.error||r.status)); }
    }catch(e){ errores.push(p.pres+': error de red'); }
  }
  if(errores.length){
    if(msgEl) msgEl.innerHTML='<span style="color:red">'+errores.join(' | ')+'</span>';
  }else{
    _toast('\u2705 Acondicionamiento registrado ('+payload.length+' presentacion'+(payload.length>1?'es':'')+')',1);
    cerrarAcondActivo();
    loadColaAcond();
    loadAcondSimple();
  }
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
async function cargarAcondPendientesLib(){
  var sel=document.getElementById('lb-acond-sel');if(!sel) return;
  if(sel.options.length>1) return;
  try{
    var r=await fetch('/api/acondicionamiento/pendientes-lib');
    var d=await r.json();var pend=d.pendientes||[];
    sel.innerHTML='<option value="">-- Selecciona batch acondicionado --</option>';
    pend.forEach(function(a){
      var op=document.createElement('option');
      op.value=a.id;op.dataset.lote=a.lote||'';op.dataset.producto=a.producto||'';
      op.dataset.pres=a.presentacion||'';op.dataset.uds=a.unidades||0;op.dataset.fecha=a.fecha||'';
      op.text=(a.lote||'?')+' - '+(a.producto||'?')+' '+a.presentacion+' ('+a.unidades+' uds)';
      sel.appendChild(op);
    });
  }catch(e){}
}
function cargarDesdeAcond(){
  var sel=document.getElementById('lb-acond-sel');if(!sel||!sel.value) return;
  var opt=sel.options[sel.selectedIndex];
  var f=function(id,v){var el=document.getElementById(id);if(el)el.value=v;};
  f('lb-acond-id',opt.value);f('lb-lote',opt.dataset.lote||'');
  f('lb-prod',opt.dataset.producto||'');f('lb-pres',opt.dataset.pres||'');
  f('lb-uds',opt.dataset.uds||'');
  var fechaEl=document.getElementById('lb-fprod');
  if(fechaEl&&opt.dataset.fecha) fechaEl.value=(opt.dataset.fecha||'').slice(0,10);
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
var _clientesLib=[];
async function cargarClientesLib(){
  try{var r=await fetch('/api/clientes');var d=await r.json();_clientesLib=(d.clientes||[]).filter(function(c){return c.activo;});}
  catch(e){_clientesLib=[];}
}
function aprobarLib(id){
  var opts=_clientesLib.map(function(c){
    var o=document.createElement("option");
    o.value=c.nombre; o.textContent=c.nombre; return o.outerHTML;
  }).join("");
  var modal=document.createElement("div");
  modal.id="lib-modal-overlay";
  modal.style.cssText="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;display:flex;align-items:center;justify-content:center;";
  modal.innerHTML=
    '<div style="background:#fff;border-radius:10px;padding:28px 32px;'
    +'min-width:340px;max-width:460px;box-shadow:0 8px 40px rgba(0,0,0,0.18);">'
    +'<h3 style="margin:0 0 18px;color:#1a2332;font-size:1.1em;">'
    +'&#128666; Confirmar Liberación</h3>'
    +'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">'
    +'Cliente destino</label>'
    +'<select id="lib-cli-sel" style="width:100%;padding:8px;border:1px solid #ccc;'
    +'border-radius:6px;font-size:0.93em;margin-bottom:14px;">'
    +'<option value="">-- Seleccionar cliente --</option>'+opts+'</select>'
    +'<label style="font-size:0.85em;color:#555;display:block;margin-bottom:5px;">'
    +'Observaciones (opcional)</label>'
    +'<input id="lib-obs-inp" type="text" '
    +'style="width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;'
    +'font-size:0.93em;margin-bottom:20px;box-sizing:border-box;" '
    +'placeholder="Ej: Conforme CC, OK BPM...">'
    +'<div style="display:flex;gap:10px;justify-content:flex-end;">'
    +'<button id="lib-cancel-btn" style="padding:8px 18px;border:1px solid #ccc;'
    +'border-radius:6px;cursor:pointer;background:#f5f5f5;font-size:0.9em;">Cancelar</button>'
    +'<button id="lib-confirm-btn" style="padding:8px 18px;background:#28a745;'
    +'color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;'
    +'font-size:0.9em;">&#10003; Liberar</button>'
    +'</div></div>';
  document.body.appendChild(modal);
  document.getElementById("lib-cancel-btn").onclick=function(){modal.remove();};
  document.getElementById("lib-confirm-btn").onclick=function(){
    var cli=document.getElementById("lib-cli-sel").value;
    var obs=document.getElementById("lib-obs-inp").value;
    modal.remove();
    fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({estado:"Liberado",cliente:cli,observaciones:obs})})
    .then(function(r){return r.json();})
    .then(function(){_toast('✅ Liberado'+(cli?' → '+cli:''),1);loadLiberaciones('');});
  };
}
function rechazarLib(id){
  var obs=prompt("Motivo de rechazo:");
  if(!obs)return;
  fetch("/api/liberacion/"+id,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({estado:"Rechazado",observaciones:obs})})
  .then(function(){loadLiberaciones("");});
}

/* ============================================================
   ENVASADO SIMPLE
   ============================================================ */
var _envSimpleMEE = [];
async function cargarEnvasadoSimpleTab(){
  // Populate product selector from formulas
  var sel = document.getElementById('env-prod-sel');
  if(sel && sel.options.length <= 1){
    try{
      var r = await fetch('/api/programacion/productos');
      var d = await r.json();
      var prods = d.formulas || [];
      if(prods.length){
        sel.innerHTML = '<option value="">-- Selecciona producto --</option>';
        prods.forEach(function(p){
          var op = document.createElement('option');
          var nombre = p.nombre || p.producto_nombre || '';
          op.value = nombre; op.text = nombre;
          sel.appendChild(op);
        });
      }
    }catch(e){}
  }
  // Populate envase/tapa selectors from MEE stock
  var selEnv = document.getElementById('env-envase-sel');
  var selTap = document.getElementById('env-tapa-sel');
  if(selEnv && selEnv.options.length <= 1){
    try{
      var rm = await fetch('/api/mee/stock');
      var dm = await rm.json();
      _envSimpleMEE = dm.items || [];
      var envCats = ['Envase','Frasco','Gotero','Tarro'];
      var envOpts = '<option value="">-- Sin envase --</option>';
      var tapOpts = '<option value="">-- Sin tapa --</option>';
      _envSimpleMEE.forEach(function(m){
        var opt = '<option value="'+m.codigo+'">'+m.codigo+' - '+m.descripcion+' (stock: '+m.stock_actual+')</option>';
        if(envCats.indexOf(m.categoria) >= 0) envOpts += opt;
        else if(m.categoria === 'Tapa') tapOpts += opt;
      });
      if(selEnv) selEnv.innerHTML = envOpts;
      if(selTap) selTap.innerHTML = tapOpts;
    }catch(e){}
  }
  // Load history
  await cargarHistEnvasado();
}

async function registrarEnvasadoSimple(){
  var prodSel = document.getElementById('env-prod-sel');
  var lote = (document.getElementById('env-lote')||{value:''}).value.trim();
  var uds = parseInt((document.getElementById('env-uds')||{value:0}).value||0);
  var pres = (document.getElementById('env-pres')||{value:''}).value.trim();
  var envCod = (document.getElementById('env-envase-sel')||{value:''}).value;
  var tapCod = (document.getElementById('env-tapa-sel')||{value:''}).value;
  var obs = (document.getElementById('env-obs')||{value:''}).value.trim();
  var producto = prodSel ? prodSel.value : '';
  if(!producto){ _toast('Selecciona un producto', 0); return; }
  if(!lote){ _toast('Ingresa el numero de lote', 0); return; }
  if(uds <= 0){ _toast('Ingresa unidades envasadas', 0); return; }
  var msg = document.getElementById('env-msg');
  if(msg) msg.innerHTML = '<span style="color:#666">Registrando...</span>';
  try{
    var r = await fetch('/api/envasado', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        produccion_id: null,
        lote: lote,
        producto: producto,
        presentacion: pres || producto,
        unidades: uds,
        envase_codigo: envCod || '',
        tapa_codigo: tapCod || '',
        operador: OPER_ACTUAL || 'Operario',
        observaciones: obs
      })
    });
    var d = await r.json();
    if(!r.ok){ if(msg) msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>'; return; }
    _toast('\u2705 Envasado registrado', 1);
    ['env-lote','env-uds','env-pres','env-obs'].forEach(function(id){ var el=document.getElementById(id); if(el) el.value=''; });
    if(prodSel) prodSel.selectedIndex = 0;
    if(msg) msg.innerHTML = '';
    await cargarHistEnvasado();
    if(typeof loadAlertasMEE === 'function') setTimeout(loadAlertasMEE, 500);
  }catch(e){
    if(msg) msg.innerHTML='<div style="color:#dc3545;padding:8px;">Error de red: '+e.message+'</div>';
  }
}

/* ============================================================
   ACONDICIONAMIENTO SIMPLE
   ============================================================ */
async function cargarAcondSimpleTab(){
  // Populate product selector
  var sel = document.getElementById('ac-prod-sel');
  if(sel && sel.options.length <= 1){
    try{
      var r = await fetch('/api/programacion/productos');
      var d = await r.json();
      var prods = d.formulas || [];
      if(prods.length){
        sel.innerHTML = '<option value="">-- Selecciona producto --</option>';
        prods.forEach(function(p){
          var nombre = p.nombre || p.producto_nombre || '';
          var op = document.createElement('option');
          op.value = nombre; op.text = nombre;
          sel.appendChild(op);
        });
      }
    }catch(e){}
  }
  // Set today as default date
  var fechaEl = document.getElementById('ac-fecha');
  if(fechaEl && !fechaEl.value) fechaEl.value = new Date().toISOString().slice(0,10);
  // Load history
  loadAcondSimple();
}

async function registrarAcondSimple(){
  var prodSel = document.getElementById('ac-prod-sel');
  var lote = (document.getElementById('ac-lote')||{value:''}).value.trim();
  var uds = parseInt((document.getElementById('ac-uds')||{value:0}).value||0);
  var fecha = (document.getElementById('ac-fecha')||{value:''}).value;
  var etiquetas = parseInt((document.getElementById('ac-etiquetas')||{value:0}).value||0);
  var plegadizas = parseInt((document.getElementById('ac-plegadizas')||{value:0}).value||0);
  var destino = (document.getElementById('ac-destino')||{value:''}).value.trim();
  var sku = (document.getElementById('ac-sku')||{value:''}).value.trim();
  var obs = (document.getElementById('ac-obs')||{value:''}).value.trim();
  var producto = prodSel ? prodSel.value : '';
  if(!producto){ _toast('Selecciona un producto', 0); return; }
  if(!lote){ _toast('Ingresa el numero de lote PT', 0); return; }
  if(uds <= 0){ _toast('Ingresa unidades acondicionadas', 0); return; }
  var obsCompleto = 'Etiquetas: '+etiquetas+' | Plegadizas: '+plegadizas+(destino?' | Destino: '+destino:'')+(obs?' | '+obs:'');
  var msgEl = document.getElementById('ac-form-msg');
  if(msgEl) msgEl.innerHTML = '<span style="color:#666">Registrando...</span>';
  try{
    var r = await fetch('/api/acondicionamiento', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        lote: lote,
        producto: producto,
        presentacion: sku || producto,
        cantidad_batch_g: 0,
        unidades_producidas: uds,
        fecha: fecha,
        observaciones: obsCompleto,
        sku: sku,
        precio_base: 0,
        mee_consumido: []
      })
    });
    var d = await r.json();
    if(!r.ok){ if(msgEl) msgEl.innerHTML='<div style="color:#dc3545;padding:8px;">Error: '+(d.error||r.status)+'</div>'; return; }
    _toast('\u2705 Batch registrado', 1);
    ['ac-lote','ac-uds','ac-etiquetas','ac-plegadizas','ac-destino','ac-sku','ac-obs'].forEach(function(id){ var el=document.getElementById(id); if(el) el.value=''; });
    if(prodSel) prodSel.selectedIndex = 0;
    if(msgEl) msgEl.innerHTML = '';
    loadAcondSimple();
  }catch(e){
    if(msgEl) msgEl.innerHTML='<div style="color:#dc3545;padding:8px;">Error de red: '+e.message+'</div>';
  }
}

function loadAcondSimple(){
  fetch('/api/acondicionamiento').then(function(r){return r.json();}).then(function(rows){
    var tb = document.getElementById('ac-tbody'); if(!tb) return;
    if(!rows.length){ tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:#999;padding:12px;">Sin registros</td></tr>'; return; }
    tb.innerHTML = rows.map(function(r){
      return '<tr style="border-bottom:1px solid #eee">' +
        '<td style="padding:7px;font-family:monospace;font-size:12px">'+r.lote+'</td>' +
        '<td style="padding:7px">'+r.producto+'</td>' +
        '<td style="padding:7px;text-align:center">'+r.unidades_producidas+'</td>' +
        '<td style="padding:7px;text-align:center;color:#555;font-size:12px">'+(r.observaciones||'--')+'</td>' +
        '<td style="padding:7px;text-align:center">'+(r.presentacion||'--')+'</td>' +
        '<td style="padding:7px;text-align:center">'+(r.sku||'--')+'</td>' +
        '<td style="padding:7px;font-size:12px">'+(r.fecha||'--')+'</td>' +
        '<td style="padding:7px;font-size:12px">'+(r.operador||'--')+'</td>' +
        '</tr>';
    }).join('');
  }).catch(function(){});
}

/* ============================================================
   PROGRAMACION — placeholder (Phase 2)
   ============================================================ */
async function sincronizarShopify(btnEl){
  if(btnEl){ btnEl.disabled=true; btnEl.textContent='Sincronizando...'; }
  try {
    var resp = await fetch('/api/programacion/sync-stock-shopify', {method:'POST', headers:{'Content-Type':'application/json'}});
    var txt = await resp.text();
    var d;
    try { d = JSON.parse(txt); } catch(pe){ alert('Error parse JSON: ' + txt.substring(0,300)); return; }
    if(d.ok){
      _toast(d.mensaje || (d.synced + ' SKUs sincronizados'), 1);
      cargarProgramacion(null);
    } else {
      alert('ERROR SYNC SHOPIFY: ' + (d.error || JSON.stringify(d)));
    }
  } catch(e){
    alert('Error de red: ' + e.message);
  } finally {
    if(btnEl){ btnEl.disabled=false; btnEl.textContent='Sincronizar Shopify'; }
  }
}

async function sincronizarVentas(btnEl){
  if(btnEl){ btnEl.disabled=true; btnEl.textContent='Sincronizando...'; }
  try {
    var resp = await fetch('/api/programacion/sync-ventas', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({days:60})});
    var txt = await resp.text();
    var d;
    try { d = JSON.parse(txt); } catch(pe){ alert('Error parse: ' + txt.substring(0,300)); return; }
    if(d.ok){
      _toast(d.mensaje || (d.synced + ' ordenes sync'), 1);
      cargarProgramacion(null);
    } else {
      alert('ERROR SYNC VENTAS: ' + (d.error || JSON.stringify(d)));
    }
  } catch(e){
    alert('Error de red: ' + e.message);
  } finally {
    if(btnEl){ btnEl.disabled=false; btnEl.textContent='Sync Ventas'; }
  }
}

async function cargarProgramacion(btnEl){
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Cargando...'; }
  var iaStatus = document.getElementById('prog-ia-status');
  if(iaStatus) iaStatus.textContent = 'Consultando Shopify + Stock + IA…';
  try{
    var r = await fetch('/api/programacion/resumen');
    var d = await r.json();
    if(d.error && !d.proyeccion){
      _toast(d.error, 0);
      if(iaStatus) iaStatus.textContent = d.error;
      return;
    }
    _renderProgramacion(d);
  }catch(e){
    _toast('Error al cargar programación: ' + e.message, 0);
    if(iaStatus) iaStatus.textContent = 'Error: ' + e.message;
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🔄 Actualizar'; }
  }
}

async function generarOCProgramacion(btnEl){
  if(!confirm('Crear solicitud de compra automática para todos los MPs faltantes?')) return;
  if(btnEl){ btnEl.disabled = true; btnEl.textContent = 'Generando...'; }
  try{
    var r = await fetch('/api/programacion/generar-oc', {method:'POST', headers:{'Content-Type':'application/json'}});
    var d = await r.json();
    if(d.ok){
      _toast('✅ ' + d.mensaje, 1);
    } else {
      _toast('Error: ' + (d.error || 'desconocido'), 0);
    }
  }catch(e){
    _toast('Error de red: ' + e.message, 0);
  }finally{
    if(btnEl){ btnEl.disabled = false; btnEl.textContent = '🛒 Generar OC'; }
  }
}

document.addEventListener('click', async function(e){
  var btn = e.target.closest('.btn-stock-init');
  if(!btn) return;
  var producto = btn.getAttribute('data-prod');
  var sku = btn.getAttribute('data-sku') || producto;
  var uds = prompt('Unidades fisicas de ' + producto + ' en bodega Espagiria (listas para ANIMUS):');
  if(!uds || isNaN(parseInt(uds)) || parseInt(uds) <= 0) return;
  var lote = prompt('Lote (Enter para auto-generar):', '');
  var body = {producto: producto, sku: sku, unidades: parseInt(uds)};
  if(lote && lote.trim()) body.lote = lote.trim();
  try{
    var r = await fetch('/api/programacion/registrar-stock', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
    var d = await r.json();
    if(d.ok){ _toast('Stock registrado: ' + d.unidades + ' uds de ' + d.producto, 1); cargarProgramacion(null); }
    else { _toast('Error: ' + (d.error||'desconocido'), 0); }
  }catch(e){ _toast('Error de red', 0); }
});

function _renderProgramacion(d){
  var vel = document.getElementById('prog-vel-val');
  var cal = document.getElementById('prog-cal-val');
  var alerts = document.getElementById('prog-alert-val');
  var iaStatus = document.getElementById('prog-ia-status');
  var iaBox = document.getElementById('prog-ia-box');
  var iaText = document.getElementById('prog-ia-text');
  if(vel && d.velocidad_total !== undefined) vel.textContent = d.velocidad_total;
  if(cal && d.proxima_produccion) cal.textContent = d.proxima_produccion;
  if(alerts && d.n_alertas !== undefined) alerts.textContent = d.n_alertas;
  if(d.narrativa_ia && iaBox && iaText){
    iaBox.style.display = 'block';
    iaText.textContent = d.narrativa_ia;
    if(iaStatus) iaStatus.textContent = 'Actualizado';
  }
  // Warnings de integridad de datos (alias collisions, calendar fail, velocidad pobre, fórmulas incompletas)
  var warnBox = document.getElementById('prog-warnings');
  if(warnBox){
    var ws = (d.warnings_datos || []);
    if(!ws.length){
      warnBox.style.display = 'none';
      warnBox.innerHTML = '';
    } else {
      warnBox.style.display = 'block';
      warnBox.innerHTML = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px 16px;margin-bottom:14px;">'
        + '<div style="font-weight:700;color:#856404;margin-bottom:8px;font-size:13px;">⚠️ ' + ws.length + ' advertencia(s) de integridad de datos</div>'
        + ws.map(function(w, idx){
            var color = w.severidad === 'alta' ? '#c00' : (w.severidad === 'media' ? '#856404' : '#666');
            var prods = '';
            if(w.productos && w.productos.length){
              prods = '<div style="font-size:11px;color:#555;margin-top:6px"><b>Productos afectados:</b> '
                    + w.productos.slice(0,5).map(function(p){
                        return '<span style="background:#fef3c7;padding:2px 7px;border-radius:6px;color:#1c1917;font-weight:600;font-size:11px">'+_escHTML(p)+'</span>';
                      }).join(' ')
                    + (w.productos.length > 5 ? ' +'+(w.productos.length-5)+' más' : '')
                    + ' <a href="/tecnica" target="_blank" style="color:#7c3aed;text-decoration:underline;margin-left:6px;font-weight:600">→ Ir a /tecnica</a>'
                    + '</div>';
            }
            // Detalle de alias_collision: mostrar variantes con boton para fusionar
            var detalleHtml = '';
            if(w.tipo === 'alias_collision' && w.detalle && w.detalle.length){
              detalleHtml = '<div style="margin-top:8px;background:#fffbeb;border:1px solid #fde68a;border-radius:6px;padding:8px 10px">'
                + '<div style="font-size:11px;font-weight:700;color:#92400e;margin-bottom:5px">🔍 MPs que colisionan:</div>'
                + w.detalle.map(function(g){
                    var vlist = (g.variantes||[]).map(function(v){
                      return '<li style="margin:3px 0"><span style="font-family:monospace;font-size:11px;background:#fef3c7;padding:1px 6px;border-radius:4px;color:#1c1917">'+_escHTML(v.codigo)+'</span> <span style="font-size:11px">'+_escHTML(v.nombre)+'</span></li>';
                    }).join('');
                    return '<div style="margin-bottom:6px;padding-bottom:6px;border-bottom:1px dashed #fde68a">'
                      + '<div style="font-size:10px;color:#78716c;margin-bottom:3px">Normalizado: <code style="background:#fff;padding:1px 5px;border-radius:3px">'+_escHTML(g.normalizado)+'</code></div>'
                      + '<ul style="margin:0;padding-left:18px">'+vlist+'</ul>'
                      + '</div>';
                  }).join('')
                + '<div style="font-size:11px;color:#475569;margin-top:6px"><b>Cómo arreglar:</b> Decide cuál nombre es el canónico, edita el otro en <a href="/inventarios" target="_blank" style="color:#7c3aed;font-weight:600">Bodega MP → Limpiar proveedores</a> o ajusta los nombres en <code>maestro_mps</code> para que sean idénticos cuando son el mismo producto.</div>'
                + '</div>';
            }
            return '<div style="font-size:12px;color:'+color+';padding:8px 0;border-top:1px dashed #e0d8a8;">'
              + '<strong>['+w.tipo+']</strong> ' + w.mensaje
              + (w.accion ? '<div style="font-size:11px;color:#666;font-style:italic;margin-top:2px;">→ ' + w.accion + '</div>' : '')
              + prods
              + detalleHtml
              + '</div>';
          }).join('')
        + '</div>';
    }
  }
  // Render projection table
  var tbody = document.getElementById('prog-tbody');
  if(tbody && d.proyeccion && d.proyeccion.length){
    tbody.innerHTML = d.proyeccion.map(function(p){
      var semColor = p.semaforo === 'verde' ? '#28a745' : p.semaforo === 'amarillo' ? '#fd7e14' : '#dc3545';
      var semEmoji = p.semaforo === 'verde' ? '\u2705' : p.semaforo === 'amarillo' ? '\u26A0\uFE0F' : '🚨';
      // MPs: ✅ all OK | ⚠️ data gap (not in movimientos) | ❌ confirmed deficit
      var mpIcon = p.mp_lista === null ? '?' :
                   (p.mp_lista === true ? '\u2705' :
                   (p.mp_lista === false ? '\u274C' :
                   (p.mp_data_gap ? '\u26A0\uFE0F' : '?')));
      // If no confirmed deficit but has data gaps, show warning instead of X
      if (p.mp_lista !== false && p.mp_data_gap) mpIcon = '\u26A0\uFE0F';
      var skuKey = p.sku || p.producto;
      var calIcon = p.cal_ok ? '\u2705' : (p.prox_produccion === 'No programado' ? '\u274C' : '\u26A0\uFE0F');
      var diasStr = p.dias_cobertura !== null && p.dias_cobertura !== undefined ? p.dias_cobertura + 'd' : '---';
      var diasColor = p.dias_cobertura < 20 ? '#dc3545' : (p.dias_cobertura < 40 ? '#fd7e14' : '#28a745');
      var isPast = p.prox_prod_pasada === true;
      var progLabel, progBtnColor;
      if (p.prox_produccion === 'No programado') {
        progLabel = '📅 Programar'; progBtnColor = '#6c757d';
      } else if (isPast) {
        progLabel = '⚠️ ' + p.prox_produccion + ' — ¿completada?'; progBtnColor = '#e67e00';
      } else {
        progLabel = '📅 ' + p.prox_produccion; progBtnColor = '#198754';
      }
      // Faltantes por horizonte: 0 = OK (verde), >0 = se queda corto (rojo)
      var f15 = p.faltante_uds_15d || 0;
      var f30 = p.faltante_uds_30d || 0;
      var f60 = p.faltante_uds_60d || 0;
      var f15Cell = f15 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f15+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      var f30Cell = f30 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f30+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      var f60Cell = f60 > 0
        ? '<span style="color:#dc2626;font-weight:700">'+f60+' uds</span>'
        : '<span style="color:#16a34a">✓</span>';
      return '<tr style="border-bottom:1px solid #eee">' +
        '<td style="padding:9px;font-weight:600">'+p.producto+'</td>' +
        '<td style="padding:9px;text-align:center">'+p.stock_actual+'</td>' +
        '<td style="padding:9px;text-align:center">'+p.vel_mes+'</td>' +
        '<td style="padding:9px;text-align:center;font-weight:700;color:'+diasColor+'">'+diasStr+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fffbeb">'+f15Cell+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fff7ed">'+f30Cell+'</td>' +
        '<td style="padding:9px;text-align:center;background:#fef2f2">'+f60Cell+'</td>' +
        '<td style="padding:9px;text-align:center">' +
          '<button data-prod="' + p.producto + '" onclick="abrirModalProgramar(this.dataset.prod)" style="background:'+progBtnColor+';color:#fff;border:none;border-radius:6px;padding:3px 9px;font-size:11px;cursor:pointer;white-space:nowrap">'+progLabel+'</button>' +
        '</td>' +
        '<td style="padding:9px;text-align:center;font-size:16px">'+calIcon+'</td>' +
        '<td style="padding:9px;text-align:center;font-size:16px">'+mpIcon+'</td>' +
        '<td style="padding:9px;text-align:center"><span style="background:'+semColor+';color:#fff;padding:3px 10px;border-radius:10px;font-size:12px">'+semEmoji+' '+p.semaforo+'</span></td>' +
        '<td style="padding:9px;text-align:center"><button class="btn-stock-init btn btn-ghost btn-sm" style="font-size:11px;padding:2px 8px" data-prod="'+p.producto+'" data-sku="'+skuKey+'">+Stock</button></td>' +
        '</tr>';
    }).join('');
  }
  // Render alerts
  var alertsDiv = document.getElementById('prog-alertas');
  if(alertsDiv && d.alertas && d.alertas.length){
    alertsDiv.innerHTML = d.alertas.map(function(a){
      var color = a.nivel === 'critico' ? '#dc3545' : a.nivel === 'alto' ? '#fd7e14' : '#ffc107';
      return '<div style="background:#fff5f5;border-left:4px solid '+color+';border-radius:4px;padding:10px 14px;margin-bottom:8px">' +
        '<div style="font-weight:600;color:'+color+';font-size:13px">\u26A0 '+a.producto+'</div>' +
        '<div style="font-size:12px;color:#555;margin-top:3px">'+a.mensaje+'</div>' +
        '</div>';
    }).join('');
  } else if(alertsDiv){
    alertsDiv.innerHTML = '<div style="text-align:center;color:#28a745;padding:20px;font-size:14px">\u2705 Sin alertas criticas</div>';
  }
}

</script>

  </div><!-- /ptab-centro -->

  <!-- PLANIFICACION ESTRATEGICA -->
  <div id="ptab-plan" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">&#128301; Planificación Estratégica de Compras</h2>
        <p style="color:#666;font-size:13px;margin:0">Calendario + Fórmulas + Stock — qué comprar, cuándo y en qué volumen</p>
      </div>
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        <span style="font-size:12px;color:#666;font-weight:600">Horizonte:</span>
        <button id="plan-btn-15"  onclick="cargarPlanificacion(15)"  style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#1a4a7a">15 días</button>
        <button id="plan-btn-30"  onclick="cargarPlanificacion(30)"  style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#1a4a7a">1 mes</button>
        <button id="plan-btn-60"  onclick="cargarPlanificacion(60)"  style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#1a4a7a;color:#fff">2 meses</button>
        <button id="plan-btn-90"  onclick="cargarPlanificacion(90)"  style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#1a4a7a">3 meses</button>
        <button id="plan-btn-180" onclick="cargarPlanificacion(180)" style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#1a4a7a">6 meses</button>
        <button id="plan-btn-365" onclick="cargarPlanificacion(365)" style="padding:6px 12px;border:2px solid #1a4a7a;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#1a4a7a">1 año</button>
      </div>
    </div>

    <div id="plan-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px"></div>

    <div id="plan-prods-box" style="display:none;background:#f0f4f8;border-radius:8px;padding:14px;margin-bottom:16px">
      <h4 style="margin:0 0 10px;color:#1a4a7a;font-size:13px">&#128197; Producciones en el horizonte</h4>
      <div id="plan-prods-list" style="display:flex;flex-wrap:wrap;gap:8px"></div>
    </div>

    <div id="plan-prods-detail-box" style="display:none;margin-bottom:20px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
        <h4 style="margin:0;color:#1a4a7a;font-size:14px">&#128269; Vista por producción — ¿qué MP alcanza y cuál no?</h4>
        <span style="font-size:11px;color:#888">Stock actual evaluado contra cada producción individualmente</span>
      </div>
      <div id="plan-prods-detail-list"></div>
    </div>

    <div id="plan-deficit-box" style="display:none;margin-bottom:20px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
        <h4 style="margin:0;color:#dc3545;font-size:14px">&#128997; MPs en déficit para el período</h4>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <button onclick="solicitarBloque()" id="btn-solicitar-bloque" style="background:#0d47a1;color:#fff;border:none;border-radius:5px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:5px" title="Crea solicitudes en el servidor agrupadas por proveedor (1 solicitud por proveedor)">&#128229; Solicitar en bloque</button>
          <button onclick="solicitarNecesidades()" id="btn-solicitar" style="background:#c0392b;color:#fff;border:none;border-radius:5px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:5px">&#128722; Solicitar (clásico)</button>
          <button onclick="descargarChecklistVerificacion()" id="btn-checklist-verif" style="background:#fd7e14;color:#fff;border:none;border-radius:5px;padding:5px 14px;font-size:12px;font-weight:700;cursor:pointer" title="Descarga Excel con dos hojas (15 dias y 1 mes) — solo MPs en cero, con casillas para que la asistente marque si estan en bodega">&#128203; Excel para verificar (15d + 1m)</button>
          <button onclick="exportarPlanificacion()" style="background:#217346;color:#fff;border:none;border-radius:5px;padding:5px 14px;font-size:12px;font-weight:600;cursor:pointer">&#128196; CSV</button>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:12px">
          <thead>
            <tr style="background:#1a4a7a;color:#fff">
              <th style="padding:9px 8px;text-align:left">Material</th>
              <th style="padding:9px 8px;text-align:left">Proveedor</th>
              <th style="padding:9px 8px;text-align:right">Necesario</th>
              <th style="padding:9px 8px;text-align:right">Stock actual</th>
              <th style="padding:9px 8px;text-align:right;color:#ffc107">Déficit</th>
              <th style="padding:9px 8px;text-align:center">Cobertura</th>
              <th style="padding:9px 8px;text-align:center">Meses</th>
              <th style="padding:9px 8px;text-align:left">Para productos</th>
            </tr>
          </thead>
          <tbody id="plan-deficit-tbody"></tbody>
        </table>
      </div>
    </div>

    <div id="plan-staff-box" style="display:none;margin-bottom:20px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:8px">
        <h4 style="margin:0;color:#1a4a7a;font-size:14px">&#128202; Staff general de Materias Primas — todas en un vistazo</h4>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <input id="plan-staff-filter" oninput="_renderStaffGeneral()" placeholder="Filtrar nombre/código..." style="padding:5px 10px;border:1px solid #ddd;border-radius:5px;font-size:12px;width:180px">
          <select id="plan-staff-state" onchange="_renderStaffGeneral()" style="padding:5px 8px;border:1px solid #ddd;border-radius:5px;font-size:12px">
            <option value="todos">Todos los estados</option>
            <option value="deficit">Solo déficit</option>
            <option value="ok">Solo OK</option>
          </select>
        </div>
      </div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:12px;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
          <thead>
            <tr style="background:#1a4a7a;color:#fff">
              <th style="padding:9px 8px;text-align:center">Estado</th>
              <th style="padding:9px 8px;text-align:left">Material</th>
              <th style="padding:9px 8px;text-align:left">Proveedor</th>
              <th style="padding:9px 8px;text-align:right">Necesario horizonte</th>
              <th style="padding:9px 8px;text-align:right">Stock actual</th>
              <th style="padding:9px 8px;text-align:right">Déficit</th>
              <th style="padding:9px 8px;text-align:center">Cobertura</th>
              <th style="padding:9px 8px;text-align:left">Productos</th>
            </tr>
          </thead>
          <tbody id="plan-staff-tbody"></tbody>
        </table>
      </div>
      <div id="plan-staff-empty" style="display:none;text-align:center;padding:20px;color:#888;font-size:12px">Sin coincidencias</div>
    </div>

    <div id="plan-ok-box" style="display:none;background:#d4edda;border-radius:8px;padding:14px;margin-bottom:16px">
      <h4 style="margin:0 0 8px;color:#155724;font-size:13px">&#10003; MPs con stock suficiente para el período</h4>
      <div id="plan-ok-list" style="display:flex;flex-wrap:wrap;gap:6px"></div>
    </div>

    <div id="plan-bulk-box" style="display:none;margin-bottom:20px">
      <h4 style="margin:0 0 12px;color:#0d47a1;font-size:14px">&#128200; Oportunidades de compra estratégica</h4>
      <div id="plan-bulk-list"></div>
    </div>

    <div id="plan-empty" style="text-align:center;padding:60px 20px;color:#888">
      <div style="font-size:48px;margin-bottom:12px">&#128301;</div>
      <div style="font-size:15px;font-weight:600;margin-bottom:6px">Análisis estratégico de materias primas</div>
      <div style="font-size:13px">Selecciona un horizonte para cruzar el calendario de producción con el stock actual</div>
    </div>
    <div id="plan-loading" style="display:none;text-align:center;padding:60px 20px;color:#1a4a7a">
      <div style="font-size:15px;font-weight:600">&#9203; Analizando calendario y fórmulas...</div>
      <div style="font-size:12px;color:#888;margin-top:6px">Puede tomar unos segundos</div>
    </div>
    <div id="plan-error" style="display:none;background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:14px;margin-bottom:16px;font-size:13px;color:#856404"></div>
  </div><!-- /ptab-plan -->

  <!-- ── Tab: Checklist Pre-Producción ────────────────────────────────── -->
  <div id="ptab-checklist" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#15803d">&#9989; Checklist Pre-Producción</h2>
        <p style="color:#666;font-size:13px;margin:0">Para cada producción programada: ¿hay materias primas, envases, etiquetas, serigrafía? · Considera demanda agregada de TODO el horizonte</p>
      </div>
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        <span style="font-size:12px;color:#666;font-weight:600">Horizonte:</span>
        <button id="ck-h-30"  onclick="cargarChecklistResumen(30)"  style="padding:6px 12px;border:2px solid #15803d;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#15803d">30 días</button>
        <button id="ck-h-60"  onclick="cargarChecklistResumen(60)"  style="padding:6px 12px;border:2px solid #15803d;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#15803d;color:#fff">60 días</button>
        <button id="ck-h-90"  onclick="cargarChecklistResumen(90)"  style="padding:6px 12px;border:2px solid #15803d;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#fff;color:#15803d">90 días</button>
        <button onclick="ckSyncCalendario()" style="padding:6px 12px;background:#1e40af;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer" title="Trae las producciones del calendario animuslb.com a la tabla de programadas">📅 Sincronizar calendario</button>
        <button onclick="ckBackfill()" style="padding:6px 12px;background:#a16207;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer" title="Genera checklists (envases, etiquetas, serigrafía) para producciones programadas sin items">🔄 Generar faltantes</button>
        <span style="margin-left:8px;font-size:11px;color:#666;font-weight:600">Auto:</span>
        <select id="ck-autorefresh" onchange="ckSetAutoRefresh(this.value)" style="padding:5px 8px;border:1px solid #d6d3d1;border-radius:6px;font-size:11px;cursor:pointer" title="Refrescar automáticamente cada N segundos. El sync con calendario se dispara en cada refresh.">
          <option value="0">off</option>
          <option value="30">30s</option>
          <option value="60" selected>1 min</option>
          <option value="180">3 min</option>
          <option value="300">5 min</option>
        </select>
      </div>
    </div>
    <div id="ck-sync-info" style="font-size:11px;color:#78716c;margin-bottom:10px;display:flex;gap:14px;flex-wrap:wrap;align-items:center">
      <span id="ck-last-sync" style="font-style:italic">última sync: —</span>
      <span id="ck-bg-info" style="color:#94a3b8">background sync activo (cada 10 min)</span>
    </div>

    <div id="ck-resumen-cards" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:18px"></div>

    <!-- Catálogo de productos con foto (sync masivo Shopify) -->
    <details id="catalogo-productos" style="margin-bottom:20px;background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px 16px">
      <summary style="cursor:pointer;font-weight:700;color:#1c1917;display:flex;align-items:center;gap:10px;list-style:none;flex-wrap:wrap">
        <span style="font-size:16px">📸 Catálogo de productos</span>
        <span id="cat-resumen" style="font-size:12px;color:#78716c;font-weight:500">cargando...</span>
        <span style="flex:1"></span>
        <button onclick="event.preventDefault();event.stopPropagation();syncShopifyAll()" id="btn-sync-all" style="padding:6px 14px;background:#10b981;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer" title="Trae fotos + SKU + descripción + precio de Shopify para todos los productos pendientes">🔄 Sincronizar todos</button>
      </summary>
      <div id="cat-grid" style="margin-top:14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px">
        <div style="grid-column:1/-1;text-align:center;color:#a8a29e;padding:20px;font-size:12px">Cargando catálogo...</div>
      </div>
    </details>

    <div id="ck-loading" style="display:none;text-align:center;padding:40px;color:#15803d;font-weight:600">Cargando producciones programadas...</div>
    <div id="ck-empty" style="display:none;text-align:center;padding:40px;color:#666;background:#fafaf9;border:1px dashed #d6d3d1;border-radius:10px;">
      <div style="font-size:36px;margin-bottom:8px">&#x1F5D3;&#xFE0F;</div>
      <div style="font-weight:700;color:#1c1917;margin-bottom:6px">Sin producciones programadas en el horizonte</div>
      <div style="font-size:12px;color:#78716c;line-height:1.5;max-width:480px;margin:0 auto 14px">
        El checklist verifica envases, etiquetas, serigrafía y tampografía de las producciones programadas. Las jala desde el calendario <b>animuslb.com</b> o de las que se programan manualmente.
      </div>
      <button onclick="ckSyncCalendario()" style="padding:8px 18px;background:#1e40af;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">&#x1F4C5; Sincronizar desde calendario</button>
    </div>

    <div id="ck-producciones-list" style="display:flex;flex-direction:column;gap:10px"></div>

    <!-- Modal detalle de un checklist -->
    <div id="ck-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;align-items:center;justify-content:center;padding:20px">
      <div style="background:#fff;border-radius:12px;padding:24px;width:900px;max-width:95vw;max-height:90vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,0.2)">
        <div id="ck-modal-header" style="display:flex;justify-content:space-between;align-items:start;margin-bottom:14px;border-bottom:2px solid #e7e5e4;padding-bottom:14px">
          <div>
            <h3 id="ck-modal-titulo" style="margin:0;color:#1c1917"></h3>
            <div id="ck-modal-sub" style="font-size:12px;color:#78716c;margin-top:4px"></div>
          </div>
          <div style="display:flex;gap:6px;align-items:center">
            <button id="ck-nav-prev" onclick="ckNavegarProducto(-1)" title="Producto anterior (←)" style="background:#f1f5f9;border:1px solid #cbd5e1;border-radius:6px;width:36px;height:32px;cursor:pointer;font-size:16px;color:#1e293b;font-weight:700;line-height:1">◀</button>
            <span id="ck-nav-pos" style="font-size:11px;color:#78716c;font-weight:600;min-width:48px;text-align:center"></span>
            <button id="ck-nav-next" onclick="ckNavegarProducto(1)" title="Siguiente producto (→)" style="background:#1e40af;border:1px solid #1e40af;border-radius:6px;width:36px;height:32px;cursor:pointer;font-size:16px;color:#fff;font-weight:700;line-height:1">▶</button>
            <button onclick="document.getElementById('ck-modal').style.display='none'" style="background:transparent;border:1px solid #d6d3d1;border-radius:6px;width:32px;height:32px;cursor:pointer;font-size:16px;color:#1c1917;font-weight:700;line-height:1;margin-left:8px" title="Cerrar (Esc)">&#10005;</button>
          </div>
        </div>
        <div id="ck-modal-progress" style="margin-bottom:14px"></div>
        <div id="ck-modal-items"></div>
      </div>
    </div>
  </div><!-- /ptab-checklist -->

  <!-- ── Tab: Tareas Operativas ─────────────────────────────────────── -->
  <div id="ptab-tareas" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#0891b2">&#127919; Tareas Operativas</h2>
        <p style="color:#666;font-size:13px;margin:0">Tareas asignadas desde Compras (Catalina) o jefes · Operarios marcan completada</p>
      </div>
      <button onclick="cargarTareasOperativas()" style="padding:6px 12px;background:#0891b2;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">&#x21BA; Actualizar</button>
    </div>
    <div id="tareas-op-lista"></div>
  </div><!-- /ptab-tareas -->

  <!-- ── ptab-plano: Centro de Mando — vista live del layout post-INVIMA ── -->
  <div id="ptab-plano" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">🎯 Centro de Mando · <span style="font-size:11px;background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;letter-spacing:1px;text-transform:uppercase;vertical-align:middle">LIVE</span> <span style="font-size:13px;color:#64748b;font-weight:500;margin-left:6px">post-INVIMA abr-2026</span></h2>
        <p style="color:#666;font-size:13px;margin:0">Estado operativo de planta en tiempo real · click una sala para iniciar/terminar producción y cambiar estado · auto-refresh cada 30s.</p>
      </div>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <input type="date" id="plano-fecha" onchange="renderCentroMando()" style="padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
        <label style="font-size:11px;color:#64748b;display:flex;align-items:center;gap:4px;cursor:pointer">
          <input type="checkbox" id="cm-auto" checked> auto-refresh 30s
        </label>
        <button onclick="renderCentroMando()" style="padding:6px 12px;background:#1a4a7a;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">↻ Refrescar</button>
        <span id="cm-last-update" style="font-size:10px;color:#94a3b8"></span>
      </div>
    </div>

    <!-- KPIs en vivo -->
    <div id="cm-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px"></div>

    <!-- KPIs actividades operarios (turnos, horas) -->
    <div id="cm-act-kpis" style="margin-bottom:14px"></div>

    <!-- Leyenda de estados -->
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px;font-size:12px;color:#475569">
      <span><span style="display:inline-block;width:14px;height:14px;background:#86efac;border:1px solid #16a34a;vertical-align:middle;margin-right:4px"></span>Libre</span>
      <span><span style="display:inline-block;width:14px;height:14px;background:#fde68a;border:1px solid #ca8a04;vertical-align:middle;margin-right:4px"></span>Ocupada (producción en curso)</span>
      <span><span style="display:inline-block;width:14px;height:14px;background:#fca5a5;border:1px solid #b91c1c;vertical-align:middle;margin-right:4px"></span>Sucia</span>
      <span><span style="display:inline-block;width:14px;height:14px;background:#93c5fd;border:1px solid #1d4ed8;vertical-align:middle;margin-right:4px"></span>Limpiando</span>
      <span><span style="display:inline-block;width:14px;height:14px;background:#cbd5e1;border:1px dashed #6b7280;vertical-align:middle;margin-right:4px"></span>Apoyo asignable (Acond/Bodega · conteos cíclicos)</span>
    </div>
    <!-- SVG fiel al plano real ASG-PRO-006-A02 (post-INVIMA abr-2026).
         Layout aproximado: el edificio tiene forma irregular, salas
         de tamaños distintos, esclusas como filtros entre zonas, y un
         bloque de servicios (comedor/baños/lockers) en la parte inferior.
         Las 5 salas asignables (PROD1-4, ENV1) tienen rect.r y son
         clickables; el resto son areas de apoyo decorativas. -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px;overflow-x:auto">
      <svg id="plano-svg" viewBox="0 0 1200 820" style="width:100%;max-width:1200px;height:auto;font-family:Segoe UI,sans-serif">
        <!-- Marco exterior del edificio -->
        <rect x="10" y="10" width="1180" height="800" fill="#fafaf9" stroke="#475569" stroke-width="2" rx="4"/>

        <!-- ── ZONA TÉCNICA SUPERIOR (esclusas, ingresos, equipos) ─────── -->
        <g>
          <rect x="20" y="20" width="100" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="70" y="46" text-anchor="middle" font-size="10" fill="#64748b">EQUIPO</text>
          <text x="70" y="60" text-anchor="middle" font-size="10" fill="#64748b">DE AGUA</text>
        </g>
        <g>
          <rect x="130" y="20" width="80" height="60" fill="#fef3c7" stroke="#ca8a04" stroke-width="1" stroke-dasharray="4 2" rx="3"/>
          <text x="170" y="46" text-anchor="middle" font-size="10" fill="#92400e" font-weight="700">ESCLUSA 1</text>
          <text x="170" y="60" text-anchor="middle" font-size="9" fill="#92400e">filtro</text>
        </g>
        <g>
          <rect x="220" y="20" width="220" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="330" y="46" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">INGRESO MATERIA PRIMA</text>
          <text x="330" y="62" text-anchor="middle" font-size="9" fill="#94a3b8">(carga · proveedores)</text>
        </g>
        <g>
          <rect x="450" y="20" width="100" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="500" y="50" text-anchor="middle" font-size="10" fill="#64748b">ESCALERA</text>
        </g>
        <g>
          <rect x="560" y="20" width="180" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="650" y="50" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">INGRESO CUBIERTA</text>
        </g>

        <!-- ── COLUMNA IZQUIERDA: lavado, ducha, almacen MP ─────────────── -->
        <g>
          <rect x="20" y="95" width="160" height="70" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="100" y="125" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">LAVADO DE</text>
          <text x="100" y="142" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">UTENSILIOS</text>
        </g>
        <g>
          <rect x="20" y="175" width="160" height="50" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="100" y="205" text-anchor="middle" font-size="11" fill="#475569">DUCHA</text>
        </g>
        <!-- Almacenamiento materia prima (vertical, izquierda, grande) — ASIGNABLE conteos cíclicos -->
        <g class="rect-area" data-codigo="ALMP" style="cursor:pointer">
          <rect class="r" x="20" y="240" width="160" height="240" fill="#cbd5e1" stroke="#6b7280" stroke-width="1.5" stroke-dasharray="6 3" rx="4"/>
          <text x="100" y="335" text-anchor="middle" font-size="12" fill="#1f2937" font-weight="700">ALMACENAMIENTO</text>
          <text x="100" y="352" text-anchor="middle" font-size="12" fill="#1f2937" font-weight="700">MATERIA PRIMA</text>
          <text x="100" y="372" text-anchor="middle" font-size="9" fill="#64748b">conteos cíclicos</text>
          <text class="status" x="100" y="395" text-anchor="middle" font-size="9" fill="#475569" font-weight="700">LIBRE</text>
        </g>

        <!-- ── COLUMNA CENTRO: dispensación, prod 2, prod 1 ─────────────── -->
        <!-- Zona de Dispensación (apoyo) -->
        <g class="rect-area" data-codigo="DISP">
          <rect x="200" y="95" width="240" height="130" fill="#e5e5e5" stroke="#94a3b8" stroke-width="1.5" rx="4"/>
          <text x="320" y="155" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">ZONA DE</text>
          <text x="320" y="173" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">DISPENSACIÓN</text>
          <text x="320" y="195" text-anchor="middle" font-size="10" fill="#64748b">(Mayerlin · fija)</text>
        </g>
        <!-- Producción 2 — con marmita 100ml — debajo de dispensación -->
        <g class="rect-area" data-codigo="PROD2" style="cursor:pointer">
          <rect class="r" x="200" y="240" width="240" height="120" fill="#86efac" stroke="#16a34a" stroke-width="2" rx="4"/>
          <text x="320" y="270" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">PRODUCCIÓN 2</text>
          <circle cx="252" cy="295" r="11" fill="#0c4a6e"/>
          <text x="252" y="299" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">M</text>
          <text x="328" y="299" text-anchor="middle" font-size="10" fill="#0c4a6e" font-weight="600">marmita 100 ml</text>
          <text x="320" y="318" text-anchor="middle" font-size="10" fill="#475569">prod + env</text>
          <text class="status" x="320" y="345" text-anchor="middle" font-size="10" fill="#16a34a" font-weight="700">LIBRE</text>
        </g>
        <!-- Producción 1 — con manejo de alcoholes — debajo de prod 2 -->
        <g class="rect-area" data-codigo="PROD1" style="cursor:pointer">
          <rect class="r" x="200" y="370" width="240" height="120" fill="#86efac" stroke="#16a34a" stroke-width="2" rx="4"/>
          <text x="320" y="400" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">PRODUCCIÓN 1</text>
          <text x="320" y="424" text-anchor="middle" font-size="11" fill="#7c2d12" font-weight="700">⚠ ALCOHOLES</text>
          <text x="320" y="442" text-anchor="middle" font-size="10" fill="#475569">prod + env</text>
          <text class="status" x="320" y="475" text-anchor="middle" font-size="10" fill="#16a34a" font-weight="700">LIBRE</text>
        </g>

        <!-- ── COLUMNA CENTRO-DERECHA: envasado 1, env 2 (ahora prod 4) ── -->
        <!-- Envasado 1 (solo envasado) -->
        <g class="rect-area" data-codigo="ENV1" style="cursor:pointer">
          <rect class="r" x="450" y="95" width="220" height="130" fill="#86efac" stroke="#16a34a" stroke-width="2" rx="4"/>
          <text x="560" y="135" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">ENVASADO 1</text>
          <text x="560" y="158" text-anchor="middle" font-size="10" fill="#475569">solo envasado</text>
          <text class="status" x="560" y="200" text-anchor="middle" font-size="10" fill="#16a34a" font-weight="700">LIBRE</text>
        </g>
        <!-- Producción 4 (era Envasado 2) -->
        <g class="rect-area" data-codigo="PROD4" style="cursor:pointer">
          <rect class="r" x="450" y="240" width="220" height="120" fill="#86efac" stroke="#16a34a" stroke-width="2" rx="4"/>
          <text x="560" y="270" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">PRODUCCIÓN 4</text>
          <text x="560" y="290" text-anchor="middle" font-size="9" fill="#94a3b8" font-style="italic">(antes Envasado 2)</text>
          <text x="560" y="312" text-anchor="middle" font-size="10" fill="#475569">prod + env</text>
          <text class="status" x="560" y="345" text-anchor="middle" font-size="10" fill="#16a34a" font-weight="700">LIBRE</text>
        </g>
        <!-- Control de calidad debajo de prod 4 -->
        <g class="rect-area" data-codigo="QC">
          <rect x="450" y="370" width="220" height="120" fill="#e5e5e5" stroke="#94a3b8" stroke-width="1.5" rx="4"/>
          <text x="560" y="420" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">CONTROL DE</text>
          <text x="560" y="438" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">CALIDAD</text>
          <text x="560" y="458" text-anchor="middle" font-size="10" fill="#64748b">(apoyo · QC)</text>
        </g>

        <!-- ── COLUMNA DERECHA: producto en proceso + esclusa 2 + acond ── -->
        <g class="rect-area" data-codigo="PIP">
          <rect x="680" y="95" width="220" height="130" fill="#e5e5e5" stroke="#94a3b8" stroke-width="1.5" rx="4"/>
          <text x="790" y="155" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">PRODUCTO EN</text>
          <text x="790" y="173" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">PROCESO</text>
          <text x="790" y="195" text-anchor="middle" font-size="10" fill="#64748b">(transición · apoyo)</text>
        </g>
        <!-- Esclusa 2 entre PIP y acondicionamiento -->
        <g>
          <rect x="680" y="240" width="80" height="50" fill="#fef3c7" stroke="#ca8a04" stroke-width="1" stroke-dasharray="4 2" rx="3"/>
          <text x="720" y="265" text-anchor="middle" font-size="10" fill="#92400e" font-weight="700">ESCLUSA 2</text>
          <text x="720" y="278" text-anchor="middle" font-size="8" fill="#92400e">filtro PT</text>
        </g>

        <!-- ── EXTREMO DERECHO: acondicionamiento PT — ASIGNABLE ────── -->
        <g class="rect-area" data-codigo="ACOND" style="cursor:pointer">
          <rect class="r" x="910" y="95" width="180" height="395" fill="#cbd5e1" stroke="#6b7280" stroke-width="1.5" stroke-dasharray="6 3" rx="4"/>
          <text x="1000" y="230" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">ACONDICIONA-</text>
          <text x="1000" y="248" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">MIENTO DE</text>
          <text x="1000" y="266" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">PRODUCTO</text>
          <text x="1000" y="284" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">TERMINADO</text>
          <text x="1000" y="305" text-anchor="middle" font-size="10" fill="#64748b">Camilo · rol predeterm.</text>
          <text x="1000" y="322" text-anchor="middle" font-size="9" fill="#1d4ed8" font-style="italic">asignable · sale a producción</text>
          <text class="status" x="1000" y="475" text-anchor="middle" font-size="10" fill="#475569" font-weight="700">LIBRE</text>
        </g>

        <!-- ── PRODUCCIÓN 3 (grande, abajo izquierda, con marmita 250) ──── -->
        <g class="rect-area" data-codigo="PROD3" style="cursor:pointer">
          <rect class="r" x="200" y="510" width="470" height="130" fill="#86efac" stroke="#16a34a" stroke-width="2" rx="4"/>
          <text x="435" y="555" text-anchor="middle" font-size="17" font-weight="700" fill="#0f172a">PRODUCCIÓN 3</text>
          <circle cx="380" cy="585" r="13" fill="#0c4a6e"/>
          <text x="380" y="590" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">M</text>
          <text x="478" y="590" text-anchor="middle" font-size="11" fill="#0c4a6e" font-weight="600">marmita 250 ml &middot; prod + env</text>
          <text class="status" x="435" y="625" text-anchor="middle" font-size="11" fill="#16a34a" font-weight="700">LIBRE</text>
        </g>
        <!-- Almacenamiento PT a la derecha de prod 3 — ASIGNABLE conteos cíclicos -->
        <g class="rect-area" data-codigo="ALMPT" style="cursor:pointer">
          <rect class="r" x="680" y="510" width="220" height="130" fill="#cbd5e1" stroke="#6b7280" stroke-width="1.5" stroke-dasharray="6 3" rx="4"/>
          <text x="790" y="555" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">ALMACENAMIENTO</text>
          <text x="790" y="573" text-anchor="middle" font-size="13" fill="#1f2937" font-weight="700">PT</text>
          <text x="790" y="595" text-anchor="middle" font-size="9" fill="#64748b">conteos cíclicos</text>
          <text class="status" x="790" y="625" text-anchor="middle" font-size="9" fill="#475569" font-weight="700">LIBRE</text>
        </g>
        <!-- Material de envase (vertical extremo derecho, abajo) -->
        <g>
          <rect x="910" y="510" width="180" height="220" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="1000" y="600" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">MATERIAL DE</text>
          <text x="1000" y="618" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">ENVASE Y</text>
          <text x="1000" y="636" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">EMPAQUE</text>
          <text x="1000" y="660" text-anchor="middle" font-size="9" fill="#94a3b8">(bodega lateral)</text>
        </g>

        <!-- ── ESCLUSA 3 + bloque de servicios (comedor/baños/lockers) ── -->
        <g>
          <rect x="20" y="500" width="160" height="50" fill="#fef3c7" stroke="#ca8a04" stroke-width="1" stroke-dasharray="4 2" rx="3"/>
          <text x="100" y="525" text-anchor="middle" font-size="10" fill="#92400e" font-weight="700">ESCLUSA 3</text>
          <text x="100" y="540" text-anchor="middle" font-size="9" fill="#92400e">salida personal</text>
        </g>
        <g>
          <rect x="20" y="560" width="160" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="100" y="585" text-anchor="middle" font-size="10" fill="#475569">UTENSILIOS</text>
          <text x="100" y="603" text-anchor="middle" font-size="10" fill="#475569">DE ASEO</text>
        </g>
        <g>
          <rect x="20" y="630" width="160" height="60" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="100" y="666" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">LOCKERS · A/C</text>
        </g>
        <g>
          <rect x="20" y="700" width="160" height="100" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="100" y="730" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">INGRESO</text>
          <text x="100" y="750" text-anchor="middle" font-size="9" fill="#94a3b8">+ ASEO</text>
          <text x="100" y="770" text-anchor="middle" font-size="9" fill="#94a3b8">+ BAÑOS · DUCHA</text>
        </g>
        <!-- Pasillo gris central (LIBRE en el plano original) -->
        <g>
          <rect x="200" y="660" width="220" height="80" fill="#e5e7eb" stroke="#94a3b8" stroke-width="1" stroke-dasharray="6 3" rx="3"/>
          <text x="310" y="695" text-anchor="middle" font-size="11" fill="#64748b" font-weight="700">PASILLO GRIS</text>
          <text x="310" y="715" text-anchor="middle" font-size="9" fill="#94a3b8" font-style="italic">circulación interna</text>
        </g>
        <!-- Comedor + cocineta -->
        <g>
          <rect x="430" y="660" width="170" height="80" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="515" y="695" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">COMEDOR</text>
          <text x="515" y="713" text-anchor="middle" font-size="9" fill="#94a3b8">break room</text>
        </g>
        <g>
          <rect x="610" y="660" width="170" height="80" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="695" y="695" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">COCINETA</text>
        </g>
        <!-- Sala de juntas + recepción material envase -->
        <g>
          <rect x="200" y="750" width="380" height="55" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="390" y="775" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">RECEPCIÓN MATERIAL ENVASE Y EMPAQUE</text>
          <text x="390" y="792" text-anchor="middle" font-size="9" fill="#94a3b8">(carga · proveedores empaque)</text>
        </g>
        <g>
          <rect x="610" y="750" width="290" height="55" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1" rx="3"/>
          <text x="755" y="780" text-anchor="middle" font-size="11" fill="#475569" font-weight="700">SALA DE JUNTAS</text>
        </g>

        <!-- Pie del SVG: nota -->
        <text x="600" y="20" text-anchor="middle" font-size="9" fill="#94a3b8" font-style="italic" opacity="0.6">Plano fiel a ASG-PRO-006-A02 · 5 salas asignables (verde) · click sala → detalle</text>
      </svg>
    </div>
    <!-- Panel detalle al lado: producciones del día por sala -->
    <div id="plano-detalle" style="margin-top:18px;display:none;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px"></div>
    <!-- Panel rotación operarios (Capa 4 visible aquí) -->
    <div id="plano-rotacion" style="margin-top:18px"></div>

    <!-- Panel gestión de operarios (CRUD) -->
    <div id="plano-crew-mgmt" style="margin-top:18px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px">
      <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:10px">
        <h3 style="margin:0;color:#1a4a7a;font-size:15px">👥 Gestión de operarios <span style="font-size:11px;color:#94a3b8;font-weight:500">(crear, editar, desactivar)</span></h3>
        <button onclick="abrirModalNuevoOperario()" style="background:#16a34a;color:#fff;border:none;padding:7px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">+ Nuevo operario</button>
      </div>
      <div id="crew-mgmt-tabla"></div>
    </div>

    <!-- Modal nuevo/editar operario -->
    <div id="modal-operario" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,0.7);z-index:9999;align-items:center;justify-content:center;padding:20px">
      <div style="background:#fff;border-radius:12px;padding:22px 26px;width:440px;max-width:95vw">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3 id="op-modal-title" style="margin:0;color:#1a4a7a;font-size:16px">Nuevo operario</h3>
          <button onclick="cerrarModalOperario()" style="background:#f1f5f9;color:#475569;border:none;padding:5px 10px;border-radius:6px;font-size:14px;cursor:pointer">×</button>
        </div>
        <input type="hidden" id="op-id">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px">
          <div>
            <label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Nombre *</label>
            <input id="op-nombre" type="text" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Apellido</label>
            <input id="op-apellido" type="text" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
        </div>
        <div style="margin-bottom:10px">
          <label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Rol predeterminado</label>
          <select id="op-rol" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            <option value="todero">Todero (rota todas las fases)</option>
            <option value="dispensacion">Dispensación</option>
            <option value="envasado">Envasado</option>
            <option value="acondicionamiento">Acondicionamiento</option>
            <option value="jefe">Jefe / Supervisor</option>
          </select>
        </div>
        <div style="display:flex;gap:14px;margin-bottom:14px">
          <label style="font-size:12px;color:#475569;cursor:pointer;display:flex;align-items:center;gap:6px">
            <input id="op-fija" type="checkbox"> Fijo en dispensación (no rota)
          </label>
          <label style="font-size:12px;color:#475569;cursor:pointer;display:flex;align-items:center;gap:6px">
            <input id="op-jefe" type="checkbox"> Es jefe de producción
          </label>
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px">
          <button onclick="cerrarModalOperario()" style="background:#f1f5f9;color:#475569;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer">Cancelar</button>
          <button onclick="guardarOperario()" style="background:#0f766e;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">Guardar</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-plano -->

  <!-- ── ptab-presentaciones: catálogo de presentaciones por SKU (Fase 0) ── -->
  <div id="ptab-presentaciones" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">&#128230; Presentaciones por Producto</h2>
        <p style="color:#666;font-size:13px;margin:0">Sueros 30/15/10 mL · contornos 15/10 mL · maxlash 4.5 mL · blush 6 g · etc. — necesario para planear "produzcamos para 2 meses"</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="abrirNuevaPresentacion()" style="background:#0f766e;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">+ Nueva presentación</button>
        <button onclick="abrirAplicarPlantilla()" style="background:#1a4a7a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">&#127979; Aplicar plantilla por categoría</button>
        <button onclick="cargarPresentaciones()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">&#x21bb; Actualizar</button>
      </div>
    </div>

    <div id="pres-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:14px"></div>

    <div id="pres-cobertura-banner" style="display:none;padding:10px 14px;border-radius:8px;background:#fef3c7;border:1px solid #fbbf24;color:#92400e;font-size:13px;margin-bottom:14px"></div>

    <div id="pres-lista" style="display:grid;grid-template-columns:1fr;gap:10px"></div>

    <!-- Modal Nueva Presentación -->
    <div id="modal-pres-nueva" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:520px;max-width:92vw;max-height:88vh;overflow:auto">
        <h3 style="margin:0 0 12px;color:#1a4a7a">+ Nueva presentación</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px">
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">Producto *</label>
            <select id="pres-producto" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Categoría</label>
            <select id="pres-categoria" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
              <option value="">— elegir —</option>
              <option value="limpiador">Limpiador</option>
              <option value="hidratante">Hidratante</option>
              <option value="suero">Suero</option>
              <option value="contorno_ojos">Contorno de ojos</option>
              <option value="maxlash">Maxlash</option>
              <option value="blush_balm">Blush balm</option>
              <option value="otro">Otro</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Código presentación *</label>
            <input id="pres-codigo" placeholder="ej. sue_30ml" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">Etiqueta visible *</label>
            <input id="pres-etiqueta" placeholder="ej. Suero 30 mL" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Volumen (mL)</label>
            <input id="pres-volumen" type="number" step="0.1" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Peso (g) — para sólidos</label>
            <input id="pres-peso" type="number" step="0.1" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Código envase MEE</label>
            <input id="pres-envase" placeholder="ej. ENV-AMBAR-30ML" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">SKU Shopify</label>
            <input id="pres-sku" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">Notas</label>
            <input id="pres-notas" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button onclick="cerrarPresModal()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="guardarPresentacion()" style="background:#0f766e;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Guardar</button>
        </div>
      </div>
    </div>

    <!-- Modal Aplicar Plantilla -->
    <div id="modal-pres-plantilla" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:480px;max-width:92vw">
        <h3 style="margin:0 0 12px;color:#1a4a7a">&#127979; Aplicar plantilla por categoría</h3>
        <p style="color:#64748b;font-size:12px;margin:0 0 12px">Crea automáticamente las presentaciones default de la categoría para un producto. Ej: <b>suero</b> → 3 presentaciones (30/15/10 mL).</p>
        <div style="display:grid;gap:10px;margin-bottom:12px">
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Producto *</label>
            <select id="plt-producto" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Categoría *</label>
            <select id="plt-categoria" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
              <option value="">— elegir —</option>
              <option value="limpiador">Limpiador (1 presentación: 150 mL)</option>
              <option value="hidratante">Hidratante (1: 50 mL airless)</option>
              <option value="suero">Suero (3: 30/15/10 mL)</option>
              <option value="contorno_ojos">Contorno ojos (2: 15 mL multipéptidos, 10 mL cafeína)</option>
              <option value="maxlash">Maxlash (1: 4.5 mL)</option>
              <option value="blush_balm">Blush balm (1: 6 g)</option>
            </select>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button onclick="cerrarPlantillaModal()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="aplicarPlantilla()" style="background:#1a4a7a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Aplicar</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-presentaciones -->

  <!-- ── ptab-equipos: catálogo de equipos del Excel (Fase 1) ── -->
  <div id="ptab-equipos" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">&#127981; Catálogo de Equipos</h2>
        <p style="color:#666;font-size:13px;margin:0">104 equipos del "LISTADO MAESTRO DE EQUIPOS 2026" — distribuidos por área. Usado por el algoritmo de sugerir-área (capacidad × lote).</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button onclick="abrirSugerirArea()" style="background:#7c3aed;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">&#x1F9E0; Probar sugerir-área</button>
        <button onclick="cargarEquipos()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">&#x21bb; Actualizar</button>
      </div>
    </div>

    <div id="eq-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px"></div>

    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:center">
      <input id="eq-search" placeholder="🔍 Buscar por código, nombre o capacidad..." oninput="filtrarEquipos()" style="flex:1;min-width:220px;padding:8px 12px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
      <select id="eq-filtro-tipo" onchange="filtrarEquipos()" style="padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
        <option value="">Todos los tipos</option>
      </select>
      <select id="eq-filtro-area" onchange="filtrarEquipos()" style="padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
        <option value="">Todas las áreas</option>
      </select>
    </div>

    <div id="eq-lista"></div>

    <!-- Modal sugerir-area -->
    <div id="modal-sugerir-area" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:580px;max-width:92vw;max-height:90vh;overflow:auto">
        <h3 style="margin:0 0 12px;color:#7c3aed">&#x1F9E0; Sugerir área para producir</h3>
        <p style="color:#64748b;font-size:12px;margin:0 0 12px">Cruza capacidad de tanques × tamaño de lote. Recomienda el tanque más pequeño que aguante con margen 20% (eficiencia).</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Producto</label>
            <input id="sa-producto" placeholder="ej. Suero X" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Tamaño lote (kg)</label>
            <input id="sa-lote" type="number" step="0.1" placeholder="ej. 80" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-bottom:14px">
          <button onclick="cerrarSugerirArea()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cerrar</button>
          <button onclick="ejecutarSugerirArea()" style="background:#7c3aed;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Calcular</button>
        </div>
        <div id="sa-resultado"></div>
      </div>
    </div>
  </div><!-- /ptab-equipos -->

  <!-- ── ptab-preflight: gates pre-flight antes de iniciar producción (Fase 2) ── -->
  <div id="ptab-preflight" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">&#128679; Pre-flight de Producción</h2>
        <p style="color:#666;font-size:13px;margin:0">Antes de iniciar, el sistema valida 6 condiciones: sala asignada, sala libre, sala limpia, MP suficientes, envases listos y operarios. Bloqueantes en rojo.</p>
      </div>
      <button onclick="cargarPreflightLista()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">&#x21bb; Actualizar</button>
    </div>

    <div id="pf-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px"></div>

    <div id="pf-lista"></div>

    <!-- Modal detalle preflight -->
    <div id="modal-preflight" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:680px;max-width:94vw;max-height:90vh;overflow:auto">
        <div id="pf-modal-header"></div>
        <div id="pf-modal-gates"></div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;border-top:1px solid #e2e8f0;padding-top:12px">
          <button onclick="cerrarPreflightModal()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cerrar</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-preflight -->

  <!-- ── ptab-plansem: Plan Semanal con consumo agregado + cascade aceptar (Fase 4) ── -->
  <div id="ptab-plansem" style="display:none">
    <div style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:18px 22px;border-radius:12px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#fff">&#128197; Plan Semanal Inteligente</h2>
        <p style="color:#cffafe;font-size:13px;margin:0">Producciones próximas con días de inventario, consumo agregado y MP. Acepta y el sistema dispara todo automático.</p>
      </div>
      <div style="display:flex;gap:8px">
        <select id="ps-dias" onchange="cargarPlanSemanal()" style="padding:8px 12px;background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.3);border-radius:6px;font-size:12px;font-weight:600">
          <option value="7">Próximos 7 días</option>
          <option value="14" selected>Próximos 14 días</option>
          <option value="20">Próximos 20 días</option>
          <option value="30">Próximos 30 días</option>
        </select>
        <button onclick="cargarPlanSemanal()" style="background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.4);padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">&#x21bb; Actualizar</button>
      </div>
    </div>

    <div id="ps-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:16px"></div>

    <div id="ps-alertas" style="display:none;background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:13px;color:#991b1b"></div>

    <div id="ps-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px"></div>

    <!-- Modal detalle producción -->
    <div id="modal-plansem" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9999;align-items:center;justify-content:center;padding:20px">
      <div style="background:#fff;border-radius:14px;width:780px;max-width:96vw;max-height:92vh;overflow:auto;box-shadow:0 20px 60px rgba(0,0,0,.4)">
        <div id="ps-modal-content"></div>
      </div>
    </div>

    <!-- Modal nuevo producto rápido -->
    <div id="modal-nuevo-producto" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:12px;padding:24px;width:520px;max-width:92vw;max-height:90vh;overflow:auto">
        <h3 style="margin:0 0 8px;color:#0f766e;font-size:18px">🆕 Nuevo producto / lanzamiento</h3>
        <p style="color:#64748b;font-size:12px;margin:0 0 14px">Crea fórmula + config de planeación + (opcional) primera producción prioritaria.</p>
        <div style="display:grid;gap:10px">
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Nombre del producto *</label>
            <input id="np-nombre" placeholder="ej. SUERO COLAGENO XX" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;text-transform:uppercase">
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Tamaño lote (kg) *</label>
              <input id="np-lote" type="number" step="0.1" placeholder="ej. 30" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            </div>
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Categoría</label>
              <select id="np-categoria" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
                <option value="">— elegir —</option>
                <option value="suero">Suero</option>
                <option value="suero_vit_c">Suero Vit C</option>
                <option value="suero_ah">Suero Ác. Hialurónico</option>
                <option value="contorno">Contorno ojos</option>
                <option value="hidratante">Hidratante</option>
                <option value="limpiador">Limpiador</option>
                <option value="esencia">Esencia</option>
                <option value="crema_corporal">Crema corporal</option>
                <option value="mascarilla">Mascarilla</option>
                <option value="maxlash">Maxlash</option>
              </select>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Cadencia (días, vacío = auto)</label>
              <input id="np-cadencia" type="number" placeholder="ej. 60" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            </div>
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Merma %</label>
              <input id="np-merma" type="number" step="0.1" value="5" style="width:100%;padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            </div>
          </div>
          <div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:8px;padding:10px 12px;color:#78350f;font-size:12px">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
              <input id="np-prioritario" type="checkbox" style="width:auto">
              <span><b>🔥 Programar primera producción ya (prioritario)</b></span>
            </label>
            <div id="np-prio-detalle" style="display:none;margin-top:8px">
              <label style="font-size:11px;color:#92400e;font-weight:600">Fecha objetivo</label>
              <input id="np-fecha" type="date" style="width:100%;padding:7px;border:1px solid #fbbf24;border-radius:5px;font-size:13px">
              <label style="font-size:11px;color:#92400e;font-weight:600;margin-top:6px;display:block">Lotes</label>
              <input id="np-lotes" type="number" min="1" value="1" style="width:100%;padding:7px;border:1px solid #fbbf24;border-radius:5px;font-size:13px">
            </div>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
          <button onclick="document.getElementById('modal-nuevo-producto').style.display='none'" style="background:#fff;border:1px solid #cbd5e1;padding:9px 18px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="guardarNuevoProducto()" style="background:#0f766e;color:#fff;border:none;padding:9px 18px;border-radius:6px;font-weight:800;cursor:pointer">✓ Crear producto</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-plansem -->

  <!-- ── ptab-autoplan: Auto-Plan Maestro (IA · cron diario 7am) ── -->
  <div id="ptab-autoplan" style="display:none">
    <div style="background:linear-gradient(135deg,#7c3aed,#dc2626);color:#fff;padding:20px 24px;border-radius:12px;margin-bottom:18px">
      <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:10px">
        <div>
          <h2 style="margin:0 0 4px;color:#fff;font-size:22px">&#129302; Auto-Plan Maestro</h2>
          <p style="margin:0;color:#fde2e4;font-size:13px;line-height:1.5">
            La planta más avanzada del mundo, <b>generada por Claude</b>. Cada lunes a las 7am el sistema:<br>
            <span style="font-size:12px">→ proyecta demanda con tendencia · → propone producciones (L/M/V) · → crea SOLs anticipadas (China 180d, local 14d) · → programa conteos cíclicos (Ma/Ju) · → notifica por email</span>
          </p>
        </div>
        <div style="display:flex;flex-direction:column;gap:6px">
          <button onclick="apPreview()" style="background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap">&#128270; Preview (dry-run)</button>
          <button onclick="apEjecutar()" style="background:#fff;color:#7c3aed;border:none;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:800;cursor:pointer;white-space:nowrap">&#128293; Ejecutar AHORA</button>
        </div>
      </div>
      <!-- Cron toggle -->
      <div style="margin-top:14px;padding:12px;background:rgba(255,255,255,.12);border-radius:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div style="font-size:12px;color:#fff">
          <b>⏰ Cron diario L-V 7am</b>:
          <span id="ap-cron-status" style="margin-left:6px">cargando...</span>
        </div>
        <button id="ap-cron-toggle-btn" onclick="apCronToggle()" style="background:#fff;color:#7c3aed;border:none;padding:6px 14px;border-radius:6px;font-size:12px;font-weight:800;cursor:pointer">Activar</button>
      </div>
    </div>

    <!-- Sub-tabs -->
    <div style="display:flex;gap:6px;margin-bottom:16px;border-bottom:2px solid #e2e8f0;padding-bottom:8px;flex-wrap:wrap">
      <button id="ap-stab-resumen" onclick="apSwitchSubtab('resumen')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#7c3aed;color:#fff">&#128202; Plan generado</button>
      <button id="ap-stab-skus" onclick="apSwitchSubtab('skus')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#475569">&#128230; Cadencias por SKU</button>
      <button id="ap-stab-mp" onclick="apSwitchSubtab('mp')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#475569">&#128230; Lead times MP/envases</button>
      <button id="ap-stab-emails" onclick="apSwitchSubtab('emails')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#475569">&#128231; Emails</button>
      <button id="ap-stab-aprendizaje" onclick="apSwitchSubtab('aprendizaje')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,#fbbf24,#dc2626);color:#fff">&#129504; Aprendizaje hist.</button>
      <button id="ap-stab-runs" onclick="apSwitchSubtab('runs')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e2e8f0;color:#475569">&#128221; Histórico runs</button>
    </div>

    <div id="ap-sub-resumen">
      <div id="ap-status-banner" style="display:none;padding:12px 16px;border-radius:8px;margin-bottom:14px;font-size:13px"></div>
      <div id="ap-resumen-content" style="text-align:center;padding:40px;color:#94a3b8">
        Pulsa <b>🔍 Preview</b> o <b>🔥 Ejecutar AHORA</b> para ver el plan generado.
      </div>
    </div>

    <div id="ap-sub-skus" style="display:none">
      <p style="color:#64748b;font-size:13px">Configura cadencia, cobertura y merma por producto. Cadencia=null significa "auto por umbral" (producir cuando bajen de cobertura mínima).</p>
      <div id="ap-skus-tabla"></div>
    </div>

    <div id="ap-sub-mp" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
        <p style="color:#64748b;font-size:13px;margin:0">Lead time + buffer por material. Envases de China = 180d lead. Local = 14d.</p>
        <button onclick="apMpNuevo()" style="background:#0f766e;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Nuevo material</button>
      </div>
      <div id="ap-mp-tabla"></div>
    </div>

    <div id="ap-sub-emails" style="display:none">
      <p style="color:#64748b;font-size:13px">Configura los correos de los roles. El sistema enviará emails automáticos (resumen diario, alertas, compras, agenda).</p>
      <div id="ap-emails-tabla"></div>
    </div>

    <div id="ap-sub-aprendizaje" style="display:none">
      <div style="background:linear-gradient(135deg,#fef3c7,#fbbf24);color:#78350f;padding:14px 18px;border-radius:10px;margin-bottom:14px">
        <h3 style="margin:0 0 4px;color:#78350f;font-size:15px">🧠 Aprendizaje del histórico</h3>
        <p style="margin:0;font-size:12px;color:#7c2d12">El sistema lee TODAS las producciones reales (Google Calendar + BD) y deriva las cadencias REALES de cada producto. Ya no tienes que configurar manualmente.</p>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap">
        <button onclick="apAnalizarHistorico()" style="background:#dc2626;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">🧠 Analizar histórico</button>
        <button onclick="apAplicarAprendizaje()" style="background:#15803d;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">✅ Aplicar TODAS las recomendaciones</button>
      </div>
      <div id="ap-aprendizaje-content" style="text-align:center;padding:30px;color:#94a3b8">
        Pulsa <b>🧠 Analizar histórico</b> para que el sistema descubra las cadencias reales.
      </div>
    </div>
    <div id="ap-sub-runs" style="display:none">
      <p style="color:#64748b;font-size:13px">Las últimas 30 ejecuciones del cron auto-plan.</p>
      <div id="ap-runs-tabla"></div>
    </div>

    <!-- Modal MP -->
    <div id="modal-mp-cfg" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:480px;max-width:92vw">
        <h3 style="margin:0 0 12px;color:#0f766e">📦 Material — lead time + buffer</h3>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px">
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">ID material *</label>
            <input id="mp-id" placeholder="ej. NIA-001" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">Nombre</label>
            <input id="mp-nombre" placeholder="ej. Niacinamida" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Origen</label>
            <select id="mp-origen" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
              <option value="local">Local (Colombia)</option>
              <option value="nacional">Nacional</option>
              <option value="china">China</option>
              <option value="usa">USA</option>
              <option value="europa">Europa</option>
              <option value="otro">Otro</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">¿Es envase?</label>
            <select id="mp-envase" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
              <option value="0">No</option><option value="1">Sí</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Lead time (días)</label>
            <input id="mp-lead" type="number" value="14" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Buffer (días)</label>
            <input id="mp-buffer" type="number" value="30" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Cobertura mín (días)</label>
            <input id="mp-cobmin" type="number" value="30" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Cobertura ideal (días)</label>
            <input id="mp-cobideal" type="number" value="60" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div style="grid-column:1/-1">
            <label style="font-size:11px;color:#64748b;font-weight:600">Proveedor principal</label>
            <input id="mp-prov" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button onclick="document.getElementById('modal-mp-cfg').style.display='none'" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="apMpGuardar()" style="background:#0f766e;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Guardar</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-autoplan -->

  <!-- ── ptab-conteo: Conteo cíclico ABC (Ma/Ju) ── -->
  <div id="ptab-conteo" style="display:none">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">&#128203; Conteo Cíclico ABC</h2>
        <p style="color:#666;font-size:13px;margin:0">Materiales contados rotativamente martes/jueves. Si stock real ≠ esperado >5% → tarea "verificar existencia real" + alerta a compras.</p>
      </div>
      <button onclick="cargarConteoCalendario()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">&#x21bb; Actualizar</button>
    </div>

    <div id="cc-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px"></div>
    <div id="cc-lista"></div>

    <!-- Modal registrar conteo -->
    <div id="modal-cc-reg" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:480px;max-width:92vw">
        <h3 id="cc-reg-titulo" style="margin:0 0 12px;color:#1a4a7a">📋 Registrar conteo</h3>
        <input id="cc-reg-id" type="hidden">
        <div style="display:grid;gap:10px">
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Stock real contado (g)</label>
            <input id="cc-reg-stock" type="number" step="0.01" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:14px;font-weight:700">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Notas (opcional)</label>
            <textarea id="cc-reg-notas" rows="3" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></textarea>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
          <button onclick="document.getElementById('modal-cc-reg').style.display='none'" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="ccRegistrar()" style="background:#0f766e;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Registrar</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-conteo -->

  <!-- ════════════════════════════════════════════════════════════════════ -->
  <!-- ptab-planv2: Plan unificado con horizontes 1sem→1año + necesidades   -->
  <!-- ════════════════════════════════════════════════════════════════════ -->
  <div id="ptab-planv2" style="display:none">
    <!-- ── HEADER COMPACTO ─────────────────────────────────────────────── -->
    <div style="background:linear-gradient(135deg,#0f766e,#0891b2);color:#fff;padding:14px 20px;border-radius:12px;margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div>
          <h2 style="margin:0;color:#fff;font-size:20px">📅 Plan de Producción Ánimus</h2>
          <div id="pv2-status-line" style="font-size:12px;color:#cffafe;margin-top:3px">⏳ Cargando estado...</div>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button onclick="abrirNuevoProducto()" style="background:#fff;color:#0f766e;border:none;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer">+ Nuevo</button>
          <button onclick="planV2DiagnosticoSKU()" style="background:#dc2626;color:#fff;border:none;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer" title="Diagnóstico SKU">🔍 Diag</button>
          <button onclick="planV2VerSemanaShopify()" style="background:#fbbf24;color:#7c2d12;border:none;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer" title="Plan semana solo Shopify">🛒 Sem</button>
          <button onclick="planV2VerLargoShopify(6)" style="background:#10b981;color:#064e3b;border:none;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer" title="Plan 6 meses">📆 6m</button>
          <button onclick="planV2VerLargoShopify(12)" style="background:#06b6d4;color:#083344;border:none;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:800;cursor:pointer" title="Plan 1 año">🗓️ 1a</button>
          <button onclick="planV2Descargar()" style="background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);color:#fff;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">📥</button>
          <button onclick="planV2Cargar()" style="background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);color:#fff;padding:7px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">↻</button>
        </div>
      </div>
      <!-- Switcher de horizonte (1 línea) -->
      <div style="display:flex;gap:6px;margin-top:12px;flex-wrap:wrap">
        <button class="phz-btn" data-meses="0.25" onclick="planV2Horizonte('0.25')" style="padding:6px 13px;border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;font-weight:700;cursor:pointer;font-size:12px">Semana</button>
        <button class="phz-btn" data-meses="1" onclick="planV2Horizonte('1')" style="padding:6px 13px;border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;font-weight:700;cursor:pointer;font-size:12px">1 mes</button>
        <button class="phz-btn" data-meses="2" onclick="planV2Horizonte('2')" style="padding:6px 13px;border:none;border-radius:6px;background:#fff;color:#0f766e;font-weight:800;cursor:pointer;font-size:12px">2 meses</button>
        <button class="phz-btn" data-meses="3" onclick="planV2Horizonte('3')" style="padding:6px 13px;border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;font-weight:700;cursor:pointer;font-size:12px">3 meses</button>
        <button class="phz-btn" data-meses="6" onclick="planV2Horizonte('6')" style="padding:6px 13px;border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;font-weight:700;cursor:pointer;font-size:12px">6 meses</button>
        <button class="phz-btn" data-meses="12" onclick="planV2Horizonte('12')" style="padding:6px 13px;border:none;border-radius:6px;background:rgba(255,255,255,.18);color:#fff;font-weight:700;cursor:pointer;font-size:12px">1 año</button>
      </div>
      <!-- Status banners ocultos (se consolidan en pv2-status-line) -->
      <div id="pv2-cobertura" style="display:none"></div>
      <div id="pv2-calendar-status" style="display:none"></div>
      <div id="pv2-auditoria" style="display:none"></div>
    </div>

    <!-- ── KPIs (1 fila) ─────────────────────────────────────────────────── -->
    <div id="pv2-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:12px"></div>

    <!-- ── CENTRO DE ACCIÓN UNIFICADO (alertas + recomendaciones en 1 panel) ─── -->
    <div id="pv2-centro-accion" style="margin-bottom:14px"></div>

    <!-- Datos crudos ocultos (los consume el centro de acción) -->
    <div id="pv2-alertas-wrap" style="display:none"></div>
    <div id="pv2-recomendaciones-wrap" style="display:none"></div>

    <!-- Sección: Comprar AHORA (urgentes por lead time) -->
    <div id="pv2-comprar-ya" style="display:none;margin-bottom:14px"></div>

    <!-- ── VISTA CALENDARIO/TIMELINE según horizonte ──────────────────── -->
    <div id="pv2-vista"></div>
  </div><!-- /ptab-planv2 -->

  <!-- ════════════════════════════════════════════════════════════════════ -->
  <!-- ptab-asignacion: Asignación semanal por área (qué hace FAB1 hoy?)    -->
  <!-- ════════════════════════════════════════════════════════════════════ -->
  <div id="ptab-asignacion" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px;color:#1a4a7a">📍 Asignación Semanal por Área</h2>
        <p style="color:#666;font-size:13px;margin:0">Qué se hace en cada sala cada día (L/M/V producir · Ma/Ju acondicionar/conteo)</p>
      </div>
      <div style="display:flex;gap:6px;align-items:center">
        <button onclick="asigSemana(-1)" style="background:#fff;border:1px solid #cbd5e1;padding:7px 12px;border-radius:6px;cursor:pointer;font-weight:600">← Anterior</button>
        <input id="asig-fecha" type="date" onchange="asigCargar()" style="padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
        <button onclick="asigSemana(1)" style="background:#fff;border:1px solid #cbd5e1;padding:7px 12px;border-radius:6px;cursor:pointer;font-weight:600">Siguiente →</button>
        <button onclick="asigSemana(0)" style="background:#0f766e;color:#fff;border:none;padding:7px 12px;border-radius:6px;cursor:pointer;font-weight:700">Hoy</button>
      </div>
    </div>
    <div id="asig-grid"></div>
  </div><!-- /ptab-asignacion -->

  <!-- ════════════════════════════════════════════════════════════════════ -->
  <!-- ptab-config: Configuración (Presentaciones + Equipos + Cadencias…)   -->
  <!-- ════════════════════════════════════════════════════════════════════ -->
  <div id="ptab-config" style="display:none">
    <div style="background:#1f2937;color:#fff;padding:16px 20px;border-radius:10px;margin-bottom:16px">
      <h2 style="margin:0;color:#fff;font-size:20px">⚙️ Configuración</h2>
      <p style="margin:4px 0 0;color:#9ca3af;font-size:12px">Setup del módulo Planta — se configura una vez, raramente se cambia</p>
    </div>
    <!-- Sub-tabs internos de Configuración -->
    <div style="display:flex;gap:6px;margin-bottom:14px;border-bottom:2px solid #e5e7eb;padding-bottom:8px;flex-wrap:wrap">
      <button id="cfg-stab-pres" onclick="cfgSubtab('pres')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#1f2937;color:#fff">📦 Presentaciones</button>
      <button id="cfg-stab-equipos" onclick="cfgSubtab('equipos')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e5e7eb;color:#475569">🏭 Equipos</button>
      <button id="cfg-stab-cadencias" onclick="cfgSubtab('cadencias')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e5e7eb;color:#475569">📦 Cadencias SKU</button>
      <button id="cfg-stab-mp" onclick="cfgSubtab('mp')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e5e7eb;color:#475569">🛒 Lead times MP</button>
      <button id="cfg-stab-emails" onclick="cfgSubtab('emails')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e5e7eb;color:#475569">📧 Emails</button>
      <button id="cfg-stab-riesgo" onclick="cfgSubtab('riesgo')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:#e5e7eb;color:#475569">🎨 Perfil Riesgo</button>
      <button id="cfg-stab-calendar" onclick="cfgSubtab('calendar')" style="padding:6px 14px;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer;background:linear-gradient(135deg,#fbbf24,#dc2626);color:#fff">📆 Google Calendar</button>
    </div>
    <div id="cfg-content"></div>
  </div><!-- /ptab-config -->

  <!-- ════════════════════════════════════════════════════════════════════ -->
  <!-- ptab-maquila: Pedidos de clientes que se suman al plan automáticamente -->
  <!-- ════════════════════════════════════════════════════════════════════ -->
  <div id="ptab-maquila" style="display:none">
    <div style="background:linear-gradient(135deg,#1a4a7a,#0891b2);color:#fff;padding:18px 22px;border-radius:12px;margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div>
          <h2 style="margin:0;color:#fff;font-size:22px">🤝 Maquila Inteligente</h2>
          <p style="margin:4px 0 0;color:#cffafe;font-size:13px">Pedidos de clientes (Kelly, Fernando…) que se SUMAN automáticamente al plan de Animus cuando comparten fórmula</p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button onclick="abrirNuevoPedido()" style="background:#fff;color:#1a4a7a;border:none;padding:8px 16px;border-radius:6px;font-weight:800;cursor:pointer">+ Nuevo pedido</button>
          <button onclick="abrirNuevoCliente()" style="background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;font-weight:700;cursor:pointer">+ Cliente</button>
        </div>
      </div>
    </div>

    <div id="mq-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px"></div>
    <div id="mq-pedidos"></div>

    <!-- Modal nuevo pedido -->
    <div id="modal-mq-pedido" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:520px;max-width:92vw;max-height:90vh;overflow:auto">
        <h3 style="margin:0 0 12px;color:#1a4a7a">+ Pedido de maquila</h3>
        <div style="display:grid;gap:10px">
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Cliente *</label>
            <select id="mq-cliente" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></select>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Producto *</label>
            <select id="mq-producto" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></select>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Unidades *</label>
              <input id="mq-unidades" type="number" min="1" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            </div>
            <div>
              <label style="font-size:11px;color:#64748b;font-weight:600">Kg estimados (opcional)</label>
              <input id="mq-kg" type="number" step="0.1" placeholder="auto si tiene presentación" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
            </div>
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Fecha entrega objetivo</label>
            <input id="mq-fecha" type="date" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
          </div>
          <div>
            <label style="font-size:11px;color:#64748b;font-weight:600">Observaciones</label>
            <textarea id="mq-obs" rows="2" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px"></textarea>
          </div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
          <button onclick="document.getElementById('modal-mq-pedido').style.display='none'" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="guardarPedidoMaquila()" style="background:#1a4a7a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Guardar pedido</button>
        </div>
      </div>
    </div>

    <!-- Modal nuevo cliente -->
    <div id="modal-mq-cliente" class="modal-bk" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;align-items:center;justify-content:center">
      <div style="background:#fff;border-radius:10px;padding:22px;width:480px;max-width:92vw">
        <h3 style="margin:0 0 12px;color:#1a4a7a">+ Cliente de maquila</h3>
        <div style="display:grid;gap:10px">
          <div><label style="font-size:11px;color:#64748b;font-weight:600">Nombre *</label><input id="mc-nombre" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px"></div>
          <div><label style="font-size:11px;color:#64748b;font-weight:600">Email</label><input id="mc-email" type="email" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px"></div>
          <div><label style="font-size:11px;color:#64748b;font-weight:600">Teléfono</label><input id="mc-tel" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px"></div>
          <div><label style="font-size:11px;color:#64748b;font-weight:600">¿Comparte fórmula con? (ej. Animus Lab)</label><input id="mc-comparte" placeholder="Animus Lab" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px"></div>
        </div>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">
          <button onclick="document.getElementById('modal-mq-cliente').style.display='none'" style="background:#fff;border:1px solid #cbd5e1;padding:8px 16px;border-radius:6px;cursor:pointer">Cancelar</button>
          <button onclick="guardarClienteMaquila()" style="background:#1a4a7a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-weight:700;cursor:pointer">Guardar cliente</button>
        </div>
      </div>
    </div>
  </div><!-- /ptab-maquila -->

  <!-- ── Asistente conversacional EOS Planta · Claude API ── -->
  <button id="ai-fab" onclick="aiTogglePanel()" title="Asistente EOS Planta · Pregúntame lo que necesites" style="position:fixed;bottom:80px;right:20px;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#dc2626);color:#fff;border:none;font-size:24px;box-shadow:0 6px 16px rgba(124,58,237,.4);cursor:pointer;z-index:9998;display:flex;align-items:center;justify-content:center">🤖</button>
  <div id="ai-panel" style="display:none;position:fixed;bottom:150px;right:20px;width:380px;max-width:92vw;height:520px;max-height:80vh;background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);z-index:9998;overflow:hidden;flex-direction:column">
    <div style="background:linear-gradient(135deg,#7c3aed,#dc2626);color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-weight:800;font-size:14px">🤖 EOS Planta</div>
        <div style="font-size:11px;opacity:.85">Asistente Claude · contexto de tu planta</div>
      </div>
      <button onclick="aiTogglePanel()" style="background:rgba(255,255,255,.18);border:none;color:#fff;width:28px;height:28px;border-radius:6px;cursor:pointer;font-size:14px">✕</button>
    </div>
    <div id="ai-messages" style="flex:1;overflow:auto;padding:14px 14px 8px;background:#f9fafb;font-size:13px"></div>
    <div style="padding:10px 12px 12px;background:#fff;border-top:1px solid #e5e7eb">
      <div style="display:flex;gap:6px">
        <input id="ai-input" placeholder="Pregúntame sobre planta, producciones, MP..." onkeydown="if(event.key==='Enter')aiEnviar()" style="flex:1;padding:9px 12px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px">
        <button onclick="aiEnviar()" id="ai-send" style="background:#7c3aed;color:#fff;border:none;padding:9px 14px;border-radius:6px;font-weight:700;cursor:pointer">▶</button>
      </div>
      <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">
        <button onclick="aiQuick('¿Cuánto Suero AH 1.5% puedo producir esta semana?')" style="background:#f3e8ff;color:#7c3aed;border:none;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer">Producir esta semana</button>
        <button onclick="aiQuick('¿Hay alertas críticas hoy?')" style="background:#fee2e2;color:#dc2626;border:none;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer">¿Alertas?</button>
        <button onclick="aiQuick('¿Qué producciones hay programadas próximas?')" style="background:#dbeafe;color:#1e40af;border:none;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer">Producciones</button>
      </div>
    </div>
  </div>

<script>
// Asistente conversacional Claude · contexto planta
var _AI_HIST = [];
function aiTogglePanel(){
  var p = document.getElementById('ai-panel');
  var open = p.style.display !== 'flex';
  p.style.display = open ? 'flex' : 'none';
  if(open && _AI_HIST.length === 0){
    aiAddMsg('assistant', '👋 Hola, soy el asistente de tu planta. Conozco las cadencias, capacidades, equipos, producciones y MP en tiempo real. Pregúntame:\\n\\n• "¿Cuánto Suero AH puedo producir esta semana?"\\n• "¿Por qué hay alerta crítica?"\\n• "¿Qué cadencia tiene Vit C?"');
  }
}
function aiAddMsg(role, txt){
  var box = document.getElementById('ai-messages');
  var bg = role==='user' ? '#7c3aed' : '#fff';
  var col = role==='user' ? '#fff' : '#0f172a';
  var border = role==='user' ? 'none' : '1px solid #e5e7eb';
  var align = role==='user' ? 'flex-end' : 'flex-start';
  var div = document.createElement('div');
  div.style.cssText = 'display:flex;justify-content:'+align+';margin-bottom:8px';
  div.innerHTML = '<div style="background:'+bg+';color:'+col+';border:'+border+';padding:9px 12px;border-radius:12px;max-width:85%;white-space:pre-wrap;line-height:1.45;font-size:13px">'+_escHTML(txt)+'</div>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}
async function aiEnviar(){
  var input = document.getElementById('ai-input');
  var pregunta = input.value.trim();
  if(!pregunta) return;
  input.value = '';
  aiAddMsg('user', pregunta);
  _AI_HIST.push({role:'user', content:pregunta});
  // Loading
  var box = document.getElementById('ai-messages');
  var loading = document.createElement('div');
  loading.id = 'ai-loading';
  loading.style.cssText = 'color:#94a3b8;font-size:11px;padding:6px 10px';
  loading.textContent = 'Pensando...';
  box.appendChild(loading);
  box.scrollTop = box.scrollHeight;
  document.getElementById('ai-send').disabled = true;
  try {
    var r = await fetch('/api/asistente/planta', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({pregunta: pregunta, historial: _AI_HIST.slice(-10)})
    });
    var d = await r.json();
    document.getElementById('ai-loading')?.remove();
    var resp = d.respuesta || d.error || 'No pude responder.';
    aiAddMsg('assistant', resp);
    if(d.respuesta) _AI_HIST.push({role:'assistant', content:d.respuesta});
  } catch(e){
    document.getElementById('ai-loading')?.remove();
    aiAddMsg('assistant', '⚠ Error de red: '+e.message);
  }
  document.getElementById('ai-send').disabled = false;
  input.focus();
}
function aiQuick(p){
  document.getElementById('ai-input').value = p;
  aiEnviar();
}
</script>

<script>
// Estado del auto-refresh
window._ckAutoRefreshTimer = null;
window._ckAutoRefreshSec = 60;
window._ckLastDias = 60;

function ckSetAutoRefresh(seg){
  // Detener timer existente
  if(window._ckAutoRefreshTimer){
    clearInterval(window._ckAutoRefreshTimer);
    window._ckAutoRefreshTimer = null;
  }
  var s = parseInt(seg||0, 10);
  window._ckAutoRefreshSec = s;
  if(!s){ return; }
  window._ckAutoRefreshTimer = setInterval(function(){
    // Pausar si la pestaña no esta visible (no quema requests innecesarios)
    if(document.visibilityState !== 'visible') return;
    // Solo si seguimos en el tab del checklist
    var tab = document.getElementById('ptab-checklist');
    if(!tab || tab.style.display === 'none') return;
    cargarChecklistResumen(window._ckLastDias);
  }, s * 1000);
}

function ckFmtRelativo(isoUtc){
  if(!isoUtc) return '—';
  try {
    var t = new Date(isoUtc).getTime();
    if(isNaN(t)) return isoUtc;
    var seg = Math.max(0, Math.round((Date.now() - t) / 1000));
    if(seg < 60) return 'hace '+seg+'s';
    var min = Math.round(seg/60);
    if(min < 60) return 'hace '+min+' min';
    var h = Math.round(min/60);
    if(h < 24) return 'hace '+h+'h';
    return 'hace '+Math.round(h/24)+'d';
  } catch(e){ return '—'; }
}

async function cargarChecklistResumen(dias){
  // Cargar catalogo de productos en paralelo (no bloquea)
  if(typeof cargarCatalogoProductos==='function') cargarCatalogoProductos();
  if(dias){
    document.querySelectorAll('[id^=ck-h-]').forEach(b=>{
      var match = b.id.match(/ck-h-(\\d+)/);
      if(match){
        var d = parseInt(match[1]);
        b.style.background = d===dias?'#15803d':'#fff';
        b.style.color      = d===dias?'#fff':'#15803d';
      }
    });
  }
  dias = dias || 60;
  window._ckLastDias = dias;
  document.getElementById('ck-loading').style.display='block';
  document.getElementById('ck-empty').style.display='none';
  document.getElementById('ck-producciones-list').innerHTML='';
  document.getElementById('ck-resumen-cards').innerHTML='';
  try {
    var r = await fetch('/api/programacion/checklist/resumen-calendario?dias='+dias);
    var d = await r.json();
    document.getElementById('ck-loading').style.display='none';
    // Indicador de ultima sincronizacion
    var sc = d.sync_calendario || {};
    var lastEl = document.getElementById('ck-last-sync');
    if(lastEl){
      var rel = ckFmtRelativo(sc.last_run_at);
      var nuevas = sc.producciones_nuevas || 0;
      lastEl.textContent = 'última sync calendario: ' + rel + (nuevas>0 ? ' · '+nuevas+' nueva(s) producción(es) importada(s)' : '');
      lastEl.style.color = sc.last_error ? '#dc2626' : '#15803d';
      if(sc.last_error){ lastEl.title = sc.last_error; }
    }
    var prods = d.producciones || [];
    if(!prods.length){
      document.getElementById('ck-empty').style.display='block';
      return;
    }
    // Cards de resumen
    var verde = prods.filter(p=>p.semaforo==='verde').length;
    var amar = prods.filter(p=>p.semaforo==='amarillo').length;
    var rojo = prods.filter(p=>p.semaforo==='rojo').length;
    var sinChecklist = prods.filter(p=>p.total_items===0).length;
    document.getElementById('ck-resumen-cards').innerHTML =
      cardKpi('Producciones', prods.length, '#1c1917', '') +
      cardKpi('🟢 Verde', verde, '#15803d', '>=90% listo') +
      cardKpi('🟡 Amarillo', amar, '#f59e0b', '50-89%') +
      cardKpi('🔴 Rojo', rojo, '#dc2626', '<50%') +
      cardKpi('Sin checklist', sinChecklist, '#78716c', 'click "Generar"');
    // Guardar lista para navegacion siguiente/anterior dentro del modal
    window._ckLista = prods.filter(function(p){ return (p.total_items||0) > 0; });
    // Lista de producciones
    document.getElementById('ck-producciones-list').innerHTML = prods.map(rowProduccion).join('');
  } catch(e){
    document.getElementById('ck-loading').style.display='none';
    document.getElementById('ck-empty').textContent='Error: '+e.message;
    document.getElementById('ck-empty').style.display='block';
  }
}

function cardKpi(label, val, color, sub){
  return '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:14px;text-align:center">' +
    '<div style="font-size:10px;color:#78716c;text-transform:uppercase;letter-spacing:0.5px;font-weight:700">'+label+'</div>' +
    '<div style="font-size:1.6em;font-weight:800;color:'+color+';margin:4px 0">'+val+'</div>' +
    (sub?'<div style="font-size:10px;color:#a8a29e">'+sub+'</div>':'') +
    '</div>';
}

function rowProduccion(p){
  var color = p.semaforo==='verde' ? '#15803d' : p.semaforo==='amarillo' ? '#f59e0b' : '#dc2626';
  var diasTxt = p.dias_faltan>=0 ? p.dias_faltan+' días' : 'hace '+Math.abs(p.dias_faltan)+'d';
  var diasColor = p.dias_faltan<0 ? '#dc2626' : p.dias_faltan<=7 ? '#f59e0b' : '#15803d';
  var pct = p.porcentaje || 0;
  var noChecklist = (p.total_items||0)===0;
  // Pills de estado: cada estado con icono propio + tooltip explicativo + color distintivo.
  // Solo se muestran los estados con count>0 para no saturar.
  var pills = '';
  function pill(cnt, ico, label, bg, fg, tip){
    if(!cnt) return '';
    return '<span title="'+tip+'" style="display:inline-flex;align-items:center;gap:3px;background:'+bg+';color:'+fg+';font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;margin:1px 0 1px 4px">'+ico+' '+cnt+'</span>';
  }
  pills += pill(p.pendientes,   '🔴', 'pend', '#fee2e2', '#991b1b', 'Pendiente — falta elegir o solicitar');
  pills += pill(p.solicitados,  '⏳', 'sol',  '#fef3c7', '#92400e', 'Solicitado — en cola de Catalina (Compras)');
  pills += pill(p.en_transito,  '🚚', 'tra',  '#dbeafe', '#1e40af', 'En tránsito — OC creada, esperando llegada');
  pills += pill(p.recibidos,    '📦', 'rec',  '#dcfce7', '#166534', 'Recibido — ya está en bodega');
  pills += pill(p.no_aplica,    '—',  'na',   '#f5f5f4', '#78716c', 'No aplica para este producto');
  // Barra de progreso visual
  var barraHtml = noChecklist ? '' :
    '<div style="background:#e7e5e4;border-radius:6px;height:8px;overflow:hidden;margin-top:6px">' +
      '<div style="background:'+color+';height:100%;width:'+pct+'%;transition:width .3s"></div>' +
    '</div>';
  // Badge de origen: distingue producciones del calendario auto-sync vs manuales
  var origenBadge = (p.origen === 'calendar')
    ? '<span title="Sincronizada desde Google Calendar" style="background:#dbeafe;color:#1e40af;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">📅 cal</span>'
    : '<span title="Entrada manual (no viene del calendario) — si esta duplicada, click ✖ para borrar" style="background:#fef3c7;color:#92400e;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">✋ man</span>';
  // Boton borrar (X) inline al lado del nombre — solo admin, valida en backend.
  var btnBorrar = '<button onclick="event.stopPropagation();ckBorrarProduccion('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+', '+JSON.stringify(p.fecha_planeada).replace(/"/g,'&quot;')+')" title="Borrar esta producción (admin) — útil para limpiar duplicados/fantasmas" style="background:transparent;color:#dc2626;border:1px solid #fca5a5;border-radius:4px;width:20px;height:20px;font-size:10px;font-weight:700;cursor:pointer;padding:0;line-height:1;margin-left:6px;vertical-align:middle">✖</button>';
  // Sebastian (29-abr-2026): badge "✅ Completada" si ya descontó inventario.
  // Si NO ha descontado y el checklist está al 80%+, botón "✅ Completar y descontar".
  var yaCompletada = !!p.descontado_at;
  var badgeCompletada = yaCompletada
    ? '<span title="Inventario descontado el '+_escHTML(p.descontado_at)+'" style="background:#dcfce7;color:#15803d;font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:6px">✅ completada</span>'
    : '';
  // Botón "Completar" si checklist >= 80% Y NO se ha descontado aún
  var btnCompletar = '';
  if(!yaCompletada && !noChecklist && pct >= 80){
    btnCompletar = '<button onclick="event.stopPropagation();ckCompletarProduccion('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')" title="Marca completada y descuenta MPs + envases del inventario" style="background:#15803d;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer;margin-top:6px;display:block;width:100%">✅ Completar y descontar</button>';
  } else if(yaCompletada){
    btnCompletar = '<button onclick="event.stopPropagation();ckRevertirCompletado('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')" title="Revertir el descuento (solo admin)" style="background:transparent;color:#0891b2;border:1px solid #67e8f9;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:600;cursor:pointer;margin-top:6px">↩ Revertir</button>';
  }
  return '<div style="background:#fff;border:1px solid #e7e5e4;border-left:4px solid '+color+';border-radius:8px;padding:14px;display:grid;grid-template-columns:1fr auto auto auto;gap:14px;align-items:center;cursor:pointer" onclick="abrirChecklistDetalle('+p.id+', '+JSON.stringify(p.producto_nombre).replace(/"/g,'&quot;')+')">' +
    '<div>' +
      '<div style="font-weight:700;font-size:14px">'+_escHTML(p.producto_nombre)+origenBadge+badgeCompletada+btnBorrar+'</div>' +
      '<div style="font-size:11px;color:#78716c;margin-top:2px">' + (p.kg||0).toLocaleString('es-CO')+' kg · ' + p.fecha_planeada + '</div>' +
      barraHtml +
    '</div>' +
    '<div style="text-align:center;min-width:80px"><div style="font-weight:800;color:'+diasColor+';font-size:1.1em">'+diasTxt+'</div><div style="font-size:10px;color:#78716c">para producir</div></div>' +
    '<div style="min-width:140px">' +
      (noChecklist
        ? '<button onclick="event.stopPropagation();ckGenerar('+p.id+')" style="background:#a16207;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-size:11px;font-weight:700;cursor:pointer">+ Generar checklist</button>'
        : '<div style="background:#f5f5f4;border-radius:8px;padding:6px 10px;text-align:center"><div style="font-weight:700;color:'+color+'">'+pct+'%</div><div style="font-size:10px;color:#78716c">'+(p.completados||0)+' de '+(p.total_items||0)+' OK</div></div>') +
      btnCompletar +
    '</div>' +
    '<div style="font-size:11px;color:#78716c;text-align:right;min-width:140px">' +
      (noChecklist ? '' : '<div style="text-align:right;line-height:1.6">'+pills+'</div>') +
      (noChecklist?'':'<div style="margin-top:4px;color:#15803d">Click para detalle →</div>') +
    '</div>' +
  '</div>';
}

async function ckGenerar(produccionId){
  try {
    var r = await fetch('/api/programacion/checklist/generar/'+produccionId, {method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast('Checklist generado: '+d.items_creados+' items', 1);
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

async function ckBackfill(){
  if(!confirm('Generar checklists para TODAS las producciones programadas que no tienen?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/backfill', {method:'POST'});
    var d = await r.json();
    if(!r.ok){
      // Error en la fase de SELECT (ej. tabla rota) — mostrar detalle
      console.error('backfill error:', d);
      alert('Error: '+(d.error||r.status)+'\\n\\nDetalle en consola (F12).');
      return;
    }
    if(d.fallas && d.fallas.length){
      // Procesado parcial — listar las fallas
      console.warn('backfill con fallas:', d.fallas);
      var lista = d.fallas.slice(0, 5).map(function(f){
        return '• '+(f.producto||'?')+' ('+(f.fecha||'')+')\\n  → '+(f.error||'').substring(0,150);
      }).join('\\n');
      alert(d.mensaje + '\\n\\nFallas (top 5 de '+d.fallas.length+'):\\n'+lista +
            '\\n\\nDetalle completo en consola (F12).');
    } else {
      _toast(d.mensaje, 1);
    }
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

// Borra y regenera el checklist de una produccion — util cuando se actualizo
// la formula (lote_size_kg / volumen_unitario_ml) y queremos recalcular las
// cantidades de envases automaticamente con la nueva info.
// Borra HARD una produccion programada (admin only — backend valida).
// Util para limpiar duplicados o fantasmas que aparecen en el horizonte.
// Sebastian (29-abr-2026): "que todo descuente que el inventario este perfecto".
// Flujo: 1) dry_run para preview. 2) confirm con detalle. 3) descuento real.
async function ckCompletarProduccion(produccionId, producto){
  if(!produccionId){ alert('ID inválido'); return; }
  try {
    // Paso 1: dry_run para mostrar preview de qué se va a descontar
    var rPrev = await fetch('/api/programacion/programar/'+produccionId+'/completar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({dry_run:true})
    });
    var rawP = await rPrev.text();
    var prev = null; try { prev = JSON.parse(rawP); } catch(_){}
    if(!rPrev.ok){
      if(prev && prev.codigo === 'YA_DESCONTADO'){
        alert('Esta producción ya descontó inventario el '+prev.inventario_descontado_at+'.\\n\\nUsa "↩ Revertir" si necesitas re-hacer el descuento.');
        return;
      }
      alert('Error: '+(prev && prev.error || rawP.substring(0,200)));
      return;
    }
    var mps = prev.mps_a_descontar || [];
    var mees = prev.mees_a_descontar || [];
    if(!mps.length && !mees.length){
      if(!confirm('Esta producción NO tiene MPs en fórmula ni envases en checklist. ¿Marcar completada igual?')) return;
    } else {
      var msg = 'Confirmar completar "'+producto+'"?\\n\\n';
      msg += 'Se descontarán del inventario:\\n';
      msg += '  • '+mps.length+' MPs ('+(prev.total_g_mps||0).toLocaleString('es-CO')+' g totales)\\n';
      msg += '  • '+mees.length+' envases/etiquetas ('+(prev.total_unidades_mees||0)+' unidades)\\n\\n';
      if(mps.length){
        msg += 'MPs principales:\\n';
        mps.slice(0,5).forEach(function(m){
          msg += '  - '+m.nombre+': '+Math.round(m.cantidad_g).toLocaleString('es-CO')+' g\\n';
        });
        if(mps.length > 5) msg += '  ...y '+(mps.length-5)+' más\\n';
      }
      msg += '\\nEsto NO se puede deshacer fácilmente (admin tiene "↩ Revertir"). ¿Continuar?';
      if(!confirm(msg)) return;
    }
    // Paso 2: descuento real
    var r = await fetch('/api/programacion/programar/'+produccionId+'/completar',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({})
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      alert('Error al descontar: '+(d && d.error || raw.substring(0,200)));
      return;
    }
    _toast('✅ '+(d.mensaje || 'Producción completada'), 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error de red: '+e.message); }
}

async function ckRevertirCompletado(produccionId, producto){
  if(!confirm('¿Revertir el descuento de "'+producto+'"?\\n\\nEsto regresará MPs y envases al inventario, y la producción volverá a estado "programado". Solo admin puede hacer esto.')) return;
  try {
    var r = await fetch('/api/programacion/programar/'+produccionId+'/revertir-completado',{
      method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'
    });
    var raw = await r.text();
    var d = null; try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      if(r.status === 403){ alert('Solo admin puede revertir.'); return; }
      alert('Error: '+(d && d.error || raw.substring(0,200)));
      return;
    }
    _toast(d.mensaje || 'Revertido', 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckBorrarProduccion(produccionId, producto, fecha){
  // Guard: si el id no llegó (fila vieja o cache stale), abortar con mensaje claro
  if(!produccionId || produccionId === 'undefined' || produccionId === 'null'){
    alert('Esta tarjeta no tiene id válido. Recarga la página (Ctrl+F5) e intenta de nuevo.');
    return;
  }
  if(!confirm('¿Borrar la producción "'+producto+'" del '+fecha+'?\\n\\nEsto la elimina DEFINITIVAMENTE junto con su checklist. Solo úsalo para duplicados o fantasmas que NO existen en el calendario.')) return;
  try {
    var r = await fetch('/api/programacion/produccion-programada/'+produccionId+'/borrar', {method:'DELETE'});
    // Robusto: parse texto crudo y solo despues intentar JSON. Si la respuesta
    // es HTML (ej. login redirect, 404 de Flask, error 502 de Render), no
    // crasheamos con "Unexpected token '<'" — mostramos el error real.
    var raw = await r.text();
    var d = null;
    try { d = JSON.parse(raw); } catch(_){}
    if(!r.ok){
      if(d && d.error){ alert('Error '+r.status+': '+d.error); }
      else if(r.status === 401){ alert('Sesión expirada. Vuelve a entrar a /login y reintenta.'); }
      else if(r.status === 403){ alert('Sin permisos. Solo Sebastian/Alejandro pueden borrar producciones.'); }
      else if(r.status === 404){ alert('Producción no encontrada. Recarga (Ctrl+F5) — quizá ya fue borrada por otro usuario.'); }
      else { alert('Error '+r.status+'. Respuesta del servidor:\\n\\n'+raw.substring(0,300)); }
      return;
    }
    _toast((d && d.mensaje) || 'Borrada', 1);
    cargarChecklistResumen(window._ckLastDias || 60);
  } catch(e){ alert('Error de red: '+e.message); }
}

async function ckRegenerar(produccionId){
  if(!confirm('Borrar y regenerar el checklist de esta producción?\\n\\nEsto recalcula MPs y envases con la presentación actual del producto. Las correcciones manuales que hayas hecho se pierden.')) return;
  try {
    var r = await fetch('/api/programacion/checklist/generar/'+produccionId, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({forzar:true})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast('Regenerado: '+(d.items_creados||0)+' items', 1);
    abrirChecklistDetalle(produccionId, window._ckCurrentProducto || '');
  } catch(e){ alert('Error: '+e.message); }
}

// Sincroniza eventos del Google Calendar (animuslb.com) → produccion_programada.
// Idempotente: usa (producto, fecha) como key. Auto-llamado al cargar el
// resumen, pero este boton da trigger manual + feedback visible.
// ─── Catálogo de productos con foto (sync masivo Shopify) ────────────
async function cargarCatalogoProductos(){
  try {
    var r = await fetch('/api/formulas/catalogo');
    var d = await r.json();
    if(!r.ok){ return; }
    var resumen = document.getElementById('cat-resumen');
    if(resumen){
      resumen.innerHTML = '<b style="color:#15803d">'+d.con_foto+'</b> con foto · '+
                          '<b style="color:#dc2626">'+d.sin_foto+'</b> sin foto · '+
                          d.total+' total';
    }
    var grid = document.getElementById('cat-grid');
    if(!grid) return;
    if(!d.productos || !d.productos.length){
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:#a8a29e;padding:20px;font-size:12px">No hay productos en formula_headers</div>';
      return;
    }
    grid.innerHTML = d.productos.map(function(p){
      var proxyUrl = '/api/imagen-producto/'+encodeURIComponent(p.nombre)+'?t='+Date.now();
      var fotoHtml;
      if(p.tiene_foto){
        fotoHtml = '<img src="'+proxyUrl+'" alt="'+_escHTML(p.nombre)+'" '+
                   'style="width:100%;height:120px;object-fit:cover;border-radius:6px;background:#f5f5f4" '+
                   'onerror="this.style.opacity=0.3">';
      } else {
        fotoHtml = '<div style="height:120px;background:#fef2f2;border:1px dashed #fca5a5;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#dc2626;font-size:11px;font-weight:600">Sin foto</div>';
      }
      var skuLine = p.sku ? '<div style="font-size:10px;color:#0f766e;font-weight:600">'+_escHTML(p.sku)+'</div>' : '';
      return '<div style="background:#fff;border:1px solid #e7e5e4;border-radius:8px;padding:8px;cursor:pointer" '+
             'onclick="catProductoClick(&quot;'+_escHTML(p.nombre).replace(/"/g,'&quot;')+'&quot;)" '+
             'title="Click para gestionar imagen">' +
        fotoHtml +
        '<div style="margin-top:6px;font-size:11px;font-weight:700;color:#1c1917;line-height:1.3;min-height:30px">'+_escHTML(p.nombre)+'</div>' +
        skuLine +
        '</div>';
    }).join('');
  } catch(e){
    console.error('catalogo:', e);
  }
}

async function syncShopifyAll(){
  var btn = document.getElementById('btn-sync-all');
  if(btn){ btn.disabled = true; btn.textContent = '⏳ Sincronizando...'; }
  try {
    var r = await fetch('/api/formulas/sync-shopify-blocking', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    var msg = '✅ '+d.sincronizados+' sincronizados';
    if(d.no_encontrados) msg += ' · ⚠️ '+d.no_encontrados+' no encontrados en Shopify';
    if(d.errores) msg += ' · ❌ '+d.errores+' errores';
    alert(msg);
    cargarCatalogoProductos();
  } catch(e){
    alert('Error de red: '+e.message);
  } finally {
    if(btn){ btn.disabled = false; btn.innerHTML = '🔄 Sincronizar todos'; }
  }
}

async function catProductoClick(nombre){
  var url = prompt('URL de imagen para "'+nombre+'" (vacío = sync Shopify):', '');
  if(url===null) return;
  url = (url||'').trim();
  if(url){
    try {
      var r = await fetch('/api/formulas/'+encodeURIComponent(nombre)+'/imagen', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({imagen_url: url})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    } catch(e){ alert('Error: '+e.message); return; }
  } else {
    // Sync Shopify del producto puntual
    try {
      var r = await fetch('/api/formulas/'+encodeURIComponent(nombre)+'/imagen-shopify-sync', {method:'POST'});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    } catch(e){ alert('Error: '+e.message); return; }
  }
  cargarCatalogoProductos();
}

async function ckSyncCalendario(){
  try {
    var r = await fetch('/api/programacion/checklist/sync-calendar?dias=90', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast(d.mensaje || 'Calendario sincronizado', 1);
    // Despues del sync, generar checklists faltantes automaticamente para
    // que las nuevas producciones aparezcan con sus items pre-poblados.
    if(d.producciones_creadas > 0){
      try { await fetch('/api/programacion/checklist/backfill', {method:'POST'}); } catch(e){}
    }
    cargarChecklistResumen();
  } catch(e){ alert('Error: '+e.message); }
}

async function abrirChecklistDetalle(produccionId, producto){
  document.getElementById('ck-modal').style.display='flex';
  document.getElementById('ck-modal-titulo').textContent = '📋 ' + producto;
  document.getElementById('ck-modal-items').innerHTML = '<div style="text-align:center;padding:40px;color:#78716c">Cargando...</div>';
  try {
    var r = await fetch('/api/programacion/checklist/'+produccionId);
    var d = await r.json();
    if(!r.ok){ document.getElementById('ck-modal-items').innerHTML='Error: '+(d.error||''); return; }
    var prim = (d.items||[])[0]||{};
    window._ckCurrentMeta = prim;  // guardar contexto para el editor inline (fecha_planeada, cantidad_kg, volumen_unitario_ml)
    var ckKg = prim.cantidad_kg||0;
    var subEl = document.getElementById('ck-modal-sub');
    if(ckKg > 0){
      subEl.innerHTML = ckKg.toLocaleString('es-CO')+' kg programada para '+(prim.fecha_planeada||'-')+
        ' &middot; <a href="javascript:void(0)" onclick="ckRegenerar('+produccionId+')" style="color:#a16207;font-size:11px;font-weight:700;text-decoration:none">🔁 Regenerar checklist</a>';
    } else {
      subEl.innerHTML = '<span style="color:#a16207">⚠️ Sin tamaño de lote — completa <code>lote_size_kg</code> en la fórmula o pon kg en el título del calendario</span>'+
        ' &middot; <a href="javascript:void(0)" onclick="ckRegenerar('+produccionId+')" style="color:#a16207;font-size:11px;font-weight:700;text-decoration:none">🔁 Regenerar</a>';
    }

    // Imagen del producto + acciones (sync Shopify, pegar URL manual)
    var imgWrap = document.getElementById('ck-modal-imagen');
    if(!imgWrap){
      imgWrap = document.createElement('div');
      imgWrap.id = 'ck-modal-imagen';
      imgWrap.style.cssText = 'margin-bottom:14px;display:flex;gap:14px;align-items:flex-start;background:#fafaf9;border:1px solid #e7e5e4;border-radius:10px;padding:12px';
      var prog = document.getElementById('ck-modal-progress');
      prog.parentNode.insertBefore(imgWrap, prog);
    }
    var prodNombre = d.producto_nombre || producto;
    var meta = d.producto_meta || {};
    // Proxy server-side para evitar hotlink/CORS de Shopify CDN
    var proxyBase = '/api/imagen-producto/' + encodeURIComponent(prodNombre);
    var imgHtml;
    if(d.imagen_url){
      imgHtml = '<img src="'+proxyBase+'?t='+Date.now()+'" alt="'+_escHTML(prodNombre)+'" '+
                'style="width:200px;height:200px;object-fit:cover;border-radius:10px;border:1px solid #e7e5e4;background:#fff;flex-shrink:0" '+
                'onerror="this.style.display=\\'none\\';if(this.nextElementSibling)this.nextElementSibling.style.display=\\'flex\\'">' +
                '<div style="display:none;width:200px;height:200px;background:#f5f5f4;border-radius:10px;align-items:center;justify-content:center;color:#a8a29e;font-size:12px;text-align:center;padding:12px;flex-shrink:0">Imagen no disponible</div>';
    } else {
      imgHtml = '<div style="width:200px;height:200px;background:#f5f5f4;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#a8a29e;font-size:12px;text-align:center;padding:12px;flex-shrink:0">Sin foto</div>';
    }
    // Galería de imagenes extra (frontal/posterior/lateral) — usa proxy
    var galeriaHtml = '';
    var imgsExtra = (meta.imagenes_extra || []).filter(function(x,i){ return i>0 && x && x.src; });
    if(imgsExtra.length){
      galeriaHtml = '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' +
        imgsExtra.slice(0,6).map(function(im, i){
          var proxyUrl = proxyBase + '?idx=' + (i+1) + '&t=' + Date.now();
          var alt = im.alt || ('Vista '+(im.position||(i+2)));
          return '<img src="'+proxyUrl+'" alt="'+_escHTML(alt)+'" title="'+_escHTML(alt)+'" '+
                 'style="width:54px;height:54px;object-fit:cover;border-radius:6px;border:1px solid #e7e5e4;cursor:pointer" '+
                 'onerror="this.style.opacity=0.3">';
        }).join('') +
        '</div>';
    }
    // Línea de SKU + precio + peso si vino de Shopify
    var bits = [];
    if(meta.sku) bits.push('<b style="color:#0f766e">SKU:</b> '+_escHTML(meta.sku));
    if(meta.precio>0) bits.push('$'+Math.round(meta.precio).toLocaleString('es-CO'));
    if(meta.peso_g>0) bits.push(Math.round(meta.peso_g)+' g');
    var metaLine = bits.length ? '<div style="font-size:11px;color:#475569;margin-top:6px">'+bits.join(' &middot; ')+'</div>' : '';
    // Descripcion preview
    var descHtml = '';
    if(meta.descripcion){
      var preview = meta.descripcion.substring(0,200) + (meta.descripcion.length>200?'…':'');
      descHtml = '<div style="font-size:11px;color:#78716c;margin-top:6px;font-style:italic;line-height:1.4">'+_escHTML(preview)+'</div>';
    }
    // Link a Shopify storefront
    var shopifyLink = '';
    if(meta.shopify_handle){
      shopifyLink = ' <a href="https://animuslb.com/products/'+_escHTML(meta.shopify_handle)+'" target="_blank" style="font-size:10px;color:#10b981;text-decoration:none;font-weight:600;margin-left:6px">↗ Ver en animuslb.com</a>';
    }

    imgWrap.innerHTML = imgHtml +
      '<div style="flex:1">' +
        '<div style="font-weight:700;font-size:15px;color:#1c1917">'+_escHTML(prodNombre)+shopifyLink+'</div>' +
        '<div style="font-size:11px;color:#78716c;margin-top:2px">'+(prim.cantidad_kg||0).toLocaleString('es-CO')+' kg &middot; '+(prim.fecha_planeada||'-')+'</div>' +
        metaLine +
        descHtml +
        galeriaHtml +
        '<div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">' +
          '<button onclick="ckImagenPegarURL(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#3b82f6;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer">📎 Pegar URL</button>' +
          '<button onclick="ckImagenShopify(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#10b981;color:#fff;border:none;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer" title="Forzar re-sync (el sync auto ya corre solo)">🔄 Re-sync</button>' +
          (d.imagen_url ? '<button onclick="ckImagenLimpiar(&quot;'+_escHTML(prodNombre).replace(/"/g,'&quot;')+'&quot;)" style="background:#fff;color:#dc2626;border:1px solid #dc2626;border-radius:5px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer">🗑️ Quitar</button>' : '') +
        '</div>' +
      '</div>';
    var pct = d.porcentaje_listo||0;
    var color = pct>=90?'#15803d':pct>=50?'#f59e0b':'#dc2626';
    document.getElementById('ck-modal-progress').innerHTML =
      '<div style="background:#f5f5f4;border-radius:8px;padding:14px;display:grid;grid-template-columns:repeat(7,1fr);gap:10px;font-size:11px">' +
      '<div><div style="color:#15803d;font-weight:800;font-size:1.4em">'+pct+'%</div><div style="color:#78716c">Listo</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.verificado_ok||0)+'</div><div style="color:#15803d">✅ Verificado</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.recibido||0)+'</div><div style="color:#15803d">📦 Recibido</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.en_transito||0)+'</div><div style="color:#1e40af">🚚 Tránsito</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.solicitado||0)+'</div><div style="color:#a16207">⏳ Solicitado</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em;color:#dc2626">'+(d.totales_por_estado.pendiente||0)+'</div><div style="color:#dc2626">🔴 Pendiente</div></div>' +
      '<div><div style="font-weight:800;font-size:1.2em">'+(d.totales_por_estado.no_aplica||0)+'</div><div style="color:#78716c">— N/A</div></div>' +
      '</div>';
    var items = d.items || [];
    if(!items.length){ document.getElementById('ck-modal-items').innerHTML='<div style="text-align:center;padding:40px;color:#78716c">Sin items en este checklist</div>'; return; }
    var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
      '<thead><tr style="background:#fafaf9;color:#78716c;font-size:11px;text-transform:uppercase">' +
      '<th style="padding:8px 10px;text-align:left">Item</th>' +
      '<th style="padding:8px 10px;text-align:right">Requerido</th>' +
      '<th style="padding:8px 10px;text-align:left">Estado / Proveedor</th>' +
      '<th style="padding:8px 10px;text-align:right">Acciones</th>' +
      '</tr></thead><tbody>';
    items.forEach(function(it){
      var icon = {mp:'⚗️',envase_primario:'🧴',tapa:'🔘',etiqueta_frontal:'🏷️',etiqueta_posterior:'🏷️',etiqueta_lateral:'🏷️',caja_exterior:'📦',serigrafia:'🎨',tampografia:'🎨',instructivo:'📄'}[it.item_tipo]||'•';
      var stCfg = {pendiente:['🔴 Pendiente','#dc2626'],verificado_ok:['✅ Verificado','#15803d'],solicitado:['⏳ Solicitado','#a16207'],en_transito:['🚚 En tránsito','#1e40af'],recibido:['📦 Recibido','#15803d'],listo:['✓ Listo','#15803d'],no_aplica:['— N/A','#78716c']}[it.estado]||['?','#78716c'];
      var cantTxt = it.cantidad_unidades>0 ? (Math.round(it.cantidad_unidades).toLocaleString('es-CO')+' und') :
                    (it.cantidad_requerida ? (Math.round(it.cantidad_requerida).toLocaleString('es-CO')+' '+(it.unidad||'g')) : '—');
      var refLink = it.solicitud_produccion_id ? '<div style="font-size:10px;color:#a16207;margin-top:2px">📋 SP-'+it.solicitud_produccion_id+'</div>' :
                    (it.solicitud_numero ? '<div style="font-size:10px;color:#a16207;margin-top:2px">'+_escHTML(it.solicitud_numero)+'</div>' :
                    (it.oc_numero ? '<div style="font-size:10px;color:#1e40af;margin-top:2px">'+_escHTML(it.oc_numero)+'</div>' : ''));
      // Tipos editables (con dropdown MEE)
      var ESEDIT = ['envase_primario','envase_secundario','tapa','etiqueta_frontal','etiqueta_posterior','etiqueta_lateral','caja_exterior','instructivo','otro'];
      var esEditable = ESEDIT.indexOf(it.item_tipo) >= 0;
      var yaTieneMee = !!it.mee_codigo_asignado;
      var canSolicitar = (it.estado==='pendiente' && !it.solicitud_produccion_id);
      var canMarcar = ['pendiente','solicitado','en_transito'].indexOf(it.estado)>=0;
      var lblElegir = yaTieneMee ? '✏️ Cambiar' : '✏️ Elegir';
      var bgElegir = yaTieneMee ? '#64748b' : '#3b82f6';
      var acciones = '';
      if(esEditable) acciones += '<button onclick="ckAbrirEditor('+it.id+',&quot;'+it.item_tipo+'&quot;,'+(it.cantidad_unidades||0)+')" style="background:'+bgElegir+';color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px">'+lblElegir+'</button>';
      if(canSolicitar) acciones += '<button onclick="ckSolicitarProduccion('+it.id+')" style="background:#a16207;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px" title="Enviar a Catalina (cola de compras)">📋 Solicitar</button>';
      if(canMarcar) acciones += '<button onclick="ckMarcar('+it.id+',&quot;recibido&quot;)" style="background:#15803d;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer;margin-right:4px">Recibido</button>';
      acciones += '<button onclick="ckMarcar('+it.id+',&quot;no_aplica&quot;)" style="background:#78716c;color:#fff;border:none;border-radius:5px;padding:4px 10px;font-size:10px;font-weight:700;cursor:pointer">N/A</button>';
      var obs = it.observaciones ? '<div style="font-size:10px;color:#78716c;margin-top:3px;font-family:monospace">'+_escHTML(it.observaciones)+'</div>' : '';
      var meeLine = yaTieneMee ? '<div style="font-size:10px;color:#0f766e;margin-top:2px"><b>MEE:</b> '+_escHTML(it.mee_codigo_asignado)+'</div>' : '';
      var decoLine = it.decoracion_tipo ? '<div style="font-size:10px;color:#7c3aed;margin-top:2px"><b>Decoración:</b> '+_escHTML(it.decoracion_tipo)+'</div>' : '';
      // Hint cuando ya hay MEE elegido pero todavía no se envió a Catalina (caso "solo guardar")
      var hintNoEnviado = (yaTieneMee && it.estado==='pendiente' && !it.solicitud_produccion_id) ?
        '<div style="font-size:10px;color:#a16207;margin-top:2px;font-style:italic">⚠️ Elegido pero no enviado a Catalina — click 📋 Solicitar</div>' : '';
      html += '<tr id="ck-row-'+it.id+'" style="border-bottom:1px solid #f5f5f4">' +
        '<td style="padding:10px"><div style="font-weight:600">'+icon+' '+_escHTML(it.descripcion)+'</div>'+(it.codigo_mp?'<div style="font-size:10px;color:#78716c">cod: '+_escHTML(it.codigo_mp)+'</div>':'')+meeLine+decoLine+obs+hintNoEnviado+'</td>' +
        '<td style="padding:10px;text-align:right;font-family:monospace">'+cantTxt+'</td>' +
        '<td style="padding:10px"><span style="color:'+stCfg[1]+';font-weight:700">'+stCfg[0]+'</span>'+(it.proveedor?'<div style="font-size:10px;color:#78716c">'+_escHTML(it.proveedor)+'</div>':'')+refLink+'</td>' +
        '<td style="padding:10px;text-align:right;white-space:nowrap">'+acciones+'</td>' +
        '</tr>';
    });
    html += '</tbody></table>';
    document.getElementById('ck-modal-items').innerHTML = html;
    // Guardar produccionId actual para refrescar despues de cambiar imagen
    window._ckCurrentProduccionId = produccionId;
    window._ckCurrentProducto = producto;
    // Actualizar botones de navegacion ◀ N/M ▶ segun posicion en la lista
    if(typeof ckActualizarNavegacion === 'function') ckActualizarNavegacion();
  } catch(e){ document.getElementById('ck-modal-items').innerHTML='Error: '+e.message; }
}

// Pegar URL de imagen manualmente (Sebastian la copia desde animuslb.com)
async function ckImagenPegarURL(producto){
  var url = prompt('URL de imagen para "'+producto+'" (ej. https://animuslb.com/cdn/...):', '');
  if(url===null) return;
  url = (url||'').trim();
  if(!url){ alert('URL vacia.'); return; }
  try {
    var r = await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({imagen_url: url})
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckImagenShopify(producto){
  try {
    var r = await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen-shopify-sync', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast('Imagen sincronizada de Shopify', 1);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckImagenLimpiar(producto){
  if(!confirm('Quitar imagen del producto "'+producto+'"?')) return;
  try {
    await fetch('/api/formulas/'+encodeURIComponent(producto)+'/imagen', {method:'DELETE'});
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

// Navegacion siguiente/anterior dentro del modal del checklist sin tener
// que cerrar y volver a abrir. Sebastian (29-abr-2026): "falta como una
// flecha para seguir al siguiente producto sin necesidad de salirse".
function ckNavegarProducto(delta){
  var lista = window._ckLista || [];
  if(!lista.length) return;
  var idActual = window._ckCurrentProduccionId;
  var idx = lista.findIndex(function(p){ return p.id === idActual; });
  if(idx < 0) return;
  var nuevoIdx = idx + delta;
  if(nuevoIdx < 0 || nuevoIdx >= lista.length) return;
  var p = lista[nuevoIdx];
  // Cerrar editor inline si esta abierto
  document.querySelectorAll('tr.ck-edit-row').forEach(function(r){ r.remove(); });
  abrirChecklistDetalle(p.id, p.producto_nombre);
}

function ckActualizarNavegacion(){
  var lista = window._ckLista || [];
  var idActual = window._ckCurrentProduccionId;
  var idx = lista.findIndex(function(p){ return p.id === idActual; });
  var prev = document.getElementById('ck-nav-prev');
  var next = document.getElementById('ck-nav-next');
  var pos  = document.getElementById('ck-nav-pos');
  if(!prev || !next || !pos) return;
  if(idx < 0 || !lista.length){
    prev.disabled = next.disabled = true;
    prev.style.opacity = next.style.opacity = '0.3';
    pos.textContent = '';
    return;
  }
  pos.textContent = (idx+1) + ' / ' + lista.length;
  // Anterior
  if(idx === 0){ prev.disabled = true; prev.style.opacity = '0.3'; prev.style.cursor = 'not-allowed'; }
  else { prev.disabled = false; prev.style.opacity = '1'; prev.style.cursor = 'pointer'; }
  // Siguiente
  if(idx === lista.length - 1){ next.disabled = true; next.style.opacity = '0.3'; next.style.cursor = 'not-allowed'; }
  else { next.disabled = false; next.style.opacity = '1'; next.style.cursor = 'pointer'; }
}

// Atajos de teclado: ← → para navegar, Esc para cerrar
document.addEventListener('keydown', function(e){
  var modal = document.getElementById('ck-modal');
  if(!modal || modal.style.display === 'none') return;
  // No interferir si el usuario esta escribiendo en un input/textarea
  var tag = (e.target && e.target.tagName || '').toLowerCase();
  if(tag === 'input' || tag === 'textarea' || tag === 'select') return;
  if(e.key === 'ArrowRight'){ e.preventDefault(); ckNavegarProducto(1); }
  else if(e.key === 'ArrowLeft'){ e.preventDefault(); ckNavegarProducto(-1); }
  else if(e.key === 'Escape'){ modal.style.display = 'none'; }
});

async function ckSolicitar(itemId){
  if(!confirm('Generar solicitud de compra para este item?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar', {method:'POST'});
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||'')); return; }
    _toast(d.mensaje||'Solicitud creada', 1);
    // Refrescar sin cerrar el modal
    cargarChecklistResumen();
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

// Editor inline (panel expandible bajo la fila — NO modal sobre modal):
// dropdown MEE + cantidad + decoracion + fecha objetivo + observaciones.
// Al guardar, dispara también solicitud a Catalina (un solo paso).
async function ckAbrirEditor(itemId, itemTipo, cantUnd){
  // Cerrar cualquier editor abierto previamente
  document.querySelectorAll('tr.ck-edit-row').forEach(function(r){ r.remove(); });

  var row = document.getElementById('ck-row-'+itemId);
  if(!row){ alert('No se encontró la fila del item.'); return; }

  // Loader inicial mientras llegan opciones MEE
  var loaderHtml = '<tr id="ck-edit-'+itemId+'" class="ck-edit-row"><td colspan="4" style="padding:0">' +
    '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px;color:#1e40af;font-size:12px">⏳ Cargando opciones MEE...</div>' +
    '</td></tr>';
  row.insertAdjacentHTML('afterend', loaderHtml);

  // Cargar opciones MEE para este tipo
  var r = await fetch('/api/checklist/mee-options?tipo='+encodeURIComponent(itemTipo));
  var d = await r.json();
  var options = d.options || [];
  window._ckEdOptions = options;
  window._ckEdSelected = null;
  window._ckEdItemId = itemId;
  window._ckEdItemTipo = itemTipo;

  var prim = window._ckCurrentMeta || {};
  var fechaDefault = prim.fecha_planeada || '';
  var soporteDeco = (itemTipo==='envase_primario' || itemTipo==='envase_secundario');

  var deco = soporteDeco ?
    '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Decoración</label>' +
    '<select id="ck-ed-deco" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0;font-size:12px">' +
      '<option value="">— Sin decoración —</option>' +
      '<option value="etiqueta_adhesiva">Etiqueta adhesiva</option>' +
      '<option value="serigrafia">Serigrafía</option>' +
      '<option value="tampografia">Tampografía</option>' +
    '</select>' : '';

  var editor = '<tr id="ck-edit-'+itemId+'" class="ck-edit-row"><td colspan="4" style="padding:0">' +
    '<div style="background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">' +
        '<div style="font-weight:700;color:#1e40af;font-size:13px">✏️ Elegir material · '+itemTipo.replace(/_/g,' ')+'</div>' +
        '<button onclick="ckCerrarEditor('+itemId+')" style="background:transparent;border:1px solid #cbd5e1;border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:14px;color:#475569;font-weight:700">×</button>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:2fr 1fr 1fr;gap:14px;align-items:start">' +
        // Col 1: buscador + lista MEE
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Material (bodega MEE)</label>' +
          '<input type="text" id="ck-ed-search" placeholder="Buscar..." oninput="ckEditorFiltrar()" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 6px;font-size:12px">' +
          '<div id="ck-ed-list" style="max-height:160px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px;background:#fff"></div>' +
        '</div>' +
        // Col 2: cantidad + decoración
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Cantidad (und)</label>' +
          '<input type="number" id="ck-ed-cant" value="'+(cantUnd||0)+'" min="0" step="1" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 10px;font-size:12px">' +
          deco +
        '</div>' +
        // Col 3: fecha objetivo + observaciones
        '<div>' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Fecha objetivo</label>' +
          '<input type="date" id="ck-ed-fecha" value="'+_escHTML(fechaDefault)+'" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0 10px;font-size:12px">' +
          '<label style="font-size:10px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px">Observaciones</label>' +
          '<textarea id="ck-ed-obs" rows="2" placeholder="Para Catalina (opcional)..." style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;margin:4px 0;font-size:12px;font-family:inherit;resize:vertical"></textarea>' +
        '</div>' +
      '</div>' +
      '<div style="display:flex;justify-content:flex-end;align-items:center;gap:10px;margin-top:12px;padding-top:10px;border-top:1px solid #c7d2fe">' +
        '<a href="javascript:void(0)" onclick="ckGuardarEditor('+itemId+',false)" style="font-size:11px;color:#475569;text-decoration:underline;cursor:pointer">solo guardar</a>' +
        '<button onclick="ckCerrarEditor('+itemId+')" style="background:#fff;border:1px solid #cbd5e1;color:#475569;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer">Cancelar</button>' +
        '<button onclick="ckGuardarEditor('+itemId+',true)" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 16px;font-size:12px;font-weight:700;cursor:pointer">💾 Guardar y enviar a Catalina</button>' +
      '</div>' +
    '</div></td></tr>';

  // Reemplazar loader con editor real
  var loader = document.getElementById('ck-edit-'+itemId);
  if(loader) loader.outerHTML = editor;
  ckEditorFiltrar();
}

function ckCerrarEditor(itemId){
  var r = document.getElementById('ck-edit-'+itemId);
  if(r) r.remove();
  window._ckEdSelected = null;
}

function ckEditorFiltrar(){
  var q = (document.getElementById('ck-ed-search').value||'').toLowerCase().trim();
  var opts = window._ckEdOptions || [];
  var filtered = q ? opts.filter(function(o){
    return (o.descripcion||'').toLowerCase().indexOf(q)>=0 ||
           (o.codigo||'').toLowerCase().indexOf(q)>=0;
  }) : opts;
  var list = document.getElementById('ck-ed-list');
  if(!filtered.length){ list.innerHTML = '<div style="padding:14px;color:#a8a29e;text-align:center;font-size:12px">Sin coincidencias</div>'; return; }
  // Render con data-codigo + listeners delegados (sin mouseover/mouseout inline que pisa la selección)
  list.innerHTML = filtered.slice(0, 60).map(function(o){
    var stockColor = o.stock>0 ? '#16a34a' : '#dc2626';
    var sel = (window._ckEdSelected === o.codigo);
    var bg = sel ? '#dbeafe' : '#fff';
    var bd = sel ? '2px solid #3b82f6' : '1px solid #f5f5f4';
    return '<div class="ck-mee-row" data-codigo="'+_escHTML(o.codigo)+'" '+
           'style="padding:8px 12px;cursor:pointer;border-bottom:'+bd+';background:'+bg+'">' +
      '<div style="font-size:13px;font-weight:600;color:#1c1917">'+(sel?'✓ ':'')+_escHTML(o.descripcion)+'</div>' +
      '<div style="font-size:10px;color:#78716c;margin-top:2px"><span style="font-family:monospace">'+_escHTML(o.codigo)+'</span> · stock: <span style="color:'+stockColor+';font-weight:600">'+Math.round(o.stock)+' '+_escHTML(o.unidad||'und')+'</span>'+(o.proveedor?' · '+_escHTML(o.proveedor):'')+'</div>' +
      '</div>';
  }).join('');
  // Adjuntar handlers via JS (no inline) — más robusto contra escapes
  list.querySelectorAll('.ck-mee-row').forEach(function(row){
    row.addEventListener('click', function(){
      ckEdSeleccionar(row.dataset.codigo);
    });
    row.addEventListener('mouseenter', function(){
      if(row.dataset.codigo !== window._ckEdSelected){ row.style.background = '#fafaf9'; }
    });
    row.addEventListener('mouseleave', function(){
      if(row.dataset.codigo !== window._ckEdSelected){ row.style.background = '#fff'; }
    });
  });
}

function ckEdSeleccionar(codigo){
  window._ckEdSelected = codigo;
  // Re-render para que el highlight (✓ + bg azul + border) sobreviva
  ckEditorFiltrar();
  // Auto-fill cantidad si no hay
  var input = document.getElementById('ck-ed-cant');
  if(input && (!input.value || parseFloat(input.value)===0)){
    var prim = (window._ckCurrentMeta||{});
    if(prim.volumen_unitario_ml > 0 && prim.cantidad_kg > 0){
      input.value = Math.ceil((prim.cantidad_kg * 1000) / prim.volumen_unitario_ml);
    }
  }
  // Mostrar el codigo seleccionado en un badge sobre el input de busqueda
  var search = document.getElementById('ck-ed-search');
  if(search){
    search.placeholder = '✓ Seleccionado: ' + codigo + ' (busca otro para cambiar)';
  }
}

// Guarda la elección + (opcional) dispara solicitud a Catalina en una sola acción.
// enviarACompras=true → asignar-mee + solicitar-produccion en cadena.
// enviarACompras=false → solo asignar-mee (preparar sin enviar todavía).
async function ckGuardarEditor(itemId, enviarACompras){
  var codigo = window._ckEdSelected;
  if(!codigo){ alert('Selecciona un material primero.'); return; }
  var cant = parseFloat(document.getElementById('ck-ed-cant').value||0);
  if(!(cant > 0)){ alert('Ingresa una cantidad mayor a 0.'); return; }
  var decoEl = document.getElementById('ck-ed-deco');
  var deco = decoEl ? (decoEl.value||'') : '';
  var fechaEl = document.getElementById('ck-ed-fecha');
  var fecha = fechaEl ? (fechaEl.value||'') : '';
  var obsEl = document.getElementById('ck-ed-obs');
  var obs = obsEl ? (obsEl.value||'').trim() : '';
  try {
    // Paso 1: guardar selección de material (asignar-mee)
    var r1 = await fetch('/api/programacion/checklist/items/'+itemId+'/asignar-mee', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({mee_codigo: codigo, cantidad_unidades: cant, decoracion_tipo: deco})
    });
    var d1 = await r1.json();
    if(!r1.ok){ alert('Error al guardar: '+(d1.error||r1.status)); return; }

    // Paso 2 (opcional): enviar a la cola de Catalina
    if(enviarACompras){
      var r2 = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar-produccion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({fecha_objetivo: fecha, observaciones: obs})
      });
      var d2 = await r2.json();
      if(!r2.ok){
        alert('Guardado, pero falló envío a Catalina: '+(d2.error||r2.status));
      } else {
        var msg = d2.ya_existia
          ? 'Ya estaba en cola de Catalina (SP-'+d2.solicitud_id+')'
          : '✓ Enviada a Catalina · SP-'+d2.solicitud_id+' · ver en /compras';
        _toast(msg, 1);
      }
    } else {
      _toast('✓ Selección guardada (no enviada todavía)', 1);
    }

    ckCerrarEditor(itemId);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckSolicitarProduccion(itemId){
  if(!confirm('Enviar solicitud a Catalina?')) return;
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId+'/solicitar-produccion', {
      method:'POST', headers:{'Content-Type':'application/json'}, body: '{}'
    });
    var d = await r.json();
    if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
    _toast(d.mensaje||'Solicitud enviada', 1);
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}

async function ckMarcar(itemId, estado){
  try {
    var r = await fetch('/api/programacion/checklist/items/'+itemId, {
      method:'PATCH',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({estado: estado, fecha_recibido: estado==='recibido'? new Date().toISOString().slice(0,10) : null})
    });
    if(!r.ok){ alert('Error'); return; }
    _toast('Item actualizado', 1);
    // Refrescar TODO sin cerrar el modal: el listado de fondo + el detalle abierto
    cargarChecklistResumen();
    if(window._ckCurrentProduccionId) abrirChecklistDetalle(window._ckCurrentProduccionId, window._ckCurrentProducto);
  } catch(e){ alert('Error: '+e.message); }
}
</script>

  <!-- ── Modal: Programar Producción ────────────────────────────────────── -->
  <div id="modal-programar" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9999;align-items:center;justify-content:center">
    <div style="background:#fff;border-radius:12px;padding:28px 32px;width:420px;max-width:95vw;box-shadow:0 8px 32px rgba(0,0,0,0.2)">
      <h3 style="margin:0 0 18px;font-size:18px;color:#1a1a2e">📅 Programar Producción</h3>
      <div style="margin-bottom:14px">
        <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:4px">Producto</label>
        <input id="mp-producto" type="text" readonly style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;background:#f8f8f8;font-size:14px;box-sizing:border-box">
      </div>
      <div style="margin-bottom:14px">
        <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:4px">Fecha de producción</label>
        <input id="mp-fecha" type="date" style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;box-sizing:border-box">
      </div>
      <div style="margin-bottom:14px">
        <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:4px">Número de lotes</label>
        <input id="mp-lotes" type="number" min="1" value="1" oninput="cargarSemaforoInsumos()" style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:14px;box-sizing:border-box">
      </div>
      <!-- Semáforo de insumos — alimentado por /api/planta/listo-producir -->
      <div id="mp-semaforo" style="margin-bottom:14px;display:none">
        <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:4px">🚦 Insumos requeridos</label>
        <div id="mp-semaforo-content" style="border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px;background:#fafafa;font-size:12px"></div>
      </div>
      <div style="margin-bottom:14px">
        <label style="font-size:13px;font-weight:600;color:#444;display:block;margin-bottom:4px">Observaciones (opcional)</label>
        <textarea id="mp-obs" rows="2" style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:6px;font-size:13px;box-sizing:border-box;resize:vertical"></textarea>
      </div>
      <!-- Asignacion post-INVIMA: sala fisica + operarios por fase -->
      <details id="mp-asignacion" style="margin-bottom:18px;border:1px solid #e0e7ff;border-radius:8px;padding:10px 12px;background:#f5f8ff" open>
        <summary style="cursor:pointer;font-size:13px;font-weight:700;color:#1e3a8a;outline:none">
          🏭 Asignar sala &amp; operarios
          <span style="font-size:11px;color:#64748b;font-weight:400;margin-left:6px">(opcional, se puede dejar y editar despues)</span>
        </summary>
        <div style="margin-top:12px">
          <label style="font-size:12px;font-weight:600;color:#444;display:block;margin-bottom:3px">Sala / Área</label>
          <select id="mp-sala" onchange="mpChequearConflictoSala()" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff">
            <option value="">— sin asignar —</option>
          </select>
          <div id="mp-sala-warn" style="font-size:11px;margin-top:4px;color:#dc2626;display:none"></div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px">
            <div>
              <label style="font-size:12px;font-weight:600;color:#444;display:block;margin-bottom:3px">Dispensación</label>
              <select id="mp-op-disp" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff">
                <option value="">—</option>
              </select>
            </div>
            <div>
              <label style="font-size:12px;font-weight:600;color:#444;display:block;margin-bottom:3px">Elaboración</label>
              <select id="mp-op-elab" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff">
                <option value="">—</option>
              </select>
            </div>
            <div>
              <label style="font-size:12px;font-weight:600;color:#444;display:block;margin-bottom:3px">Envasado</label>
              <select id="mp-op-env" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff">
                <option value="">—</option>
              </select>
            </div>
            <div>
              <label style="font-size:12px;font-weight:600;color:#444;display:block;margin-bottom:3px">Acondicionamiento</label>
              <select id="mp-op-acon" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff">
                <option value="">—</option>
              </select>
            </div>
          </div>
        </div>
      </details>
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button onclick="cerrarModalProgramar()" style="background:#f0f0f0;color:#444;border:none;border-radius:6px;padding:9px 20px;font-size:14px;cursor:pointer">Cancelar</button>
        <button onclick="guardarProgramacion()" style="background:#0d6efd;color:#fff;border:none;border-radius:6px;padding:9px 20px;font-size:14px;font-weight:600;cursor:pointer">💾 Guardar</button>
      </div>
      <!-- Upcoming events list for this product -->
      <div id="mp-eventos-lista" style="margin-top:18px;border-top:1px solid #eee;padding-top:14px;display:none">
        <div style="font-size:12px;font-weight:600;color:#666;margin-bottom:8px">Producciones programadas</div>
        <div id="mp-eventos-items"></div>
      </div>
    </div>
  </div>

</div><!-- /padding wrapper -->
</div><!-- /programacion -->

  <script>
  // ── Programar Producción Modal ───────────────────────────────────────────
  // Cache global de areas + operarios (cargado al abrir modal, sirve tambien
  // para vista de listado y futura vista plano interactivo).
  var _PLANTA_AREAS = null;
  var _PLANTA_OPERARIOS = null;

  async function _mpCargarCatalogos(){
    try{
      var r1 = await fetch('/api/planta/areas');
      var d1 = await r1.json();
      _PLANTA_AREAS = d1.areas || [];
    }catch(e){ _PLANTA_AREAS = []; }
    try{
      var r2 = await fetch('/api/planta/operarios');
      var d2 = await r2.json();
      _PLANTA_OPERARIOS = d2.operarios || [];
    }catch(e){ _PLANTA_OPERARIOS = []; }
  }

  function _mpPoblarSelectores(){
    // Sala — etiqueta enriquecida con capacidades para que se vea cual sirve
    var sel = document.getElementById('mp-sala');
    sel.innerHTML = '<option value="">— sin asignar —</option>' +
      (_PLANTA_AREAS||[]).map(function(a){
        var caps = [];
        if(a.puede_producir) caps.push('prod');
        if(a.puede_envasar)  caps.push('env');
        if(a.marmita_ml)     caps.push('marmita ' + a.marmita_ml + 'ml');
        if(a.especial)       caps.push(a.especial);
        return '<option value="'+a.id+'">'+a.nombre+'  ('+caps.join(' · ')+')</option>';
      }).join('');

    // Operarios — armar 4 selects con defaults segun rol_predeterminado.
    // Mayerlin (fija_dispensacion=true) se preselecciona y bloquea el slot.
    var ops = _PLANTA_OPERARIOS || [];
    var faseToOpDefault = {disp:null, elab:null, env:null, acon:null};
    ops.forEach(function(o){
      if (o.es_jefe) return;
      if (o.fija_dispensacion)                faseToOpDefault.disp = o.id;
      else if (o.rol === 'envasado')          faseToOpDefault.env  = o.id;
      else if (o.rol === 'acondicionamiento') faseToOpDefault.acon = o.id;
      else if (o.rol === 'todero' && faseToOpDefault.elab===null) faseToOpDefault.elab = o.id;
    });
    function _opt(o){ return '<option value="'+o.id+'">'+o.nombre_completo+(o.fija_dispensacion?' 🔒':'')+'</option>'; }
    var optsHTML = '<option value="">—</option>' +
      ops.filter(function(o){ return !o.es_jefe; }).map(_opt).join('');
    ['mp-op-disp','mp-op-elab','mp-op-env','mp-op-acon'].forEach(function(id){
      document.getElementById(id).innerHTML = optsHTML;
    });
    // Aplicar defaults
    if(faseToOpDefault.disp) document.getElementById('mp-op-disp').value = faseToOpDefault.disp;
    if(faseToOpDefault.elab) document.getElementById('mp-op-elab').value = faseToOpDefault.elab;
    if(faseToOpDefault.env)  document.getElementById('mp-op-env').value  = faseToOpDefault.env;
    if(faseToOpDefault.acon) document.getElementById('mp-op-acon').value = faseToOpDefault.acon;
  }

  async function mpChequearConflictoSala(){
    var sala_id = document.getElementById('mp-sala').value;
    var fecha   = document.getElementById('mp-fecha').value;
    var warn    = document.getElementById('mp-sala-warn');
    warn.style.display = 'none'; warn.textContent = '';
    if(!sala_id || !fecha) return;
    try{
      var r = await fetch('/api/planta/areas?fecha='+encodeURIComponent(fecha));
      var d = await r.json();
      var sala = (d.areas||[]).find(function(a){ return String(a.id)===String(sala_id); });
      if(sala && sala.ocupada_por && sala.ocupada_por.length){
        var nombres = sala.ocupada_por.map(function(o){ return o.producto; }).join(', ');
        warn.textContent = '⚠️ Esa sala ya tiene producción ese día: ' + nombres + '. Igual puedes asignarla, decides tú.';
        warn.style.display = 'block';
      }
    }catch(e){}
  }

  async function abrirModalProgramar(producto) {
    document.getElementById('mp-producto').value = producto;
    var d = new Date(); d.setDate(d.getDate() + 3);
    document.getElementById('mp-fecha').value = d.toISOString().slice(0,10);
    document.getElementById('mp-lotes').value = 1;
    document.getElementById('mp-obs').value = '';
    cargarEventosProducto(producto);
    var m = document.getElementById('modal-programar');
    m.style.display = 'flex';
    // Cargar catalogos solo la primera vez
    if(_PLANTA_AREAS===null) await _mpCargarCatalogos();
    _mpPoblarSelectores();
    // Cargar semáforo de insumos
    cargarSemaforoInsumos();
    // Listener para re-chequear conflicto cuando cambia fecha
    var fInp = document.getElementById('mp-fecha');
    if(!fInp._planta_listener){
      fInp.addEventListener('change', mpChequearConflictoSala);
      fInp._planta_listener = true;
    }
  }

  async function cargarSemaforoInsumos(){
    var producto = document.getElementById('mp-producto').value;
    var lotes = parseInt(document.getElementById('mp-lotes').value) || 1;
    var box = document.getElementById('mp-semaforo');
    var content = document.getElementById('mp-semaforo-content');
    if(!producto){ box.style.display='none'; return; }
    box.style.display = 'block';
    content.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:8px">⏳ Calculando...</div>';
    try{
      var r = await fetch('/api/planta/listo-producir/'+encodeURIComponent(producto)+'?lotes='+lotes);
      if(!r.ok){
        if(r.status === 404){
          content.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:8px">📋 Sin fórmula registrada para este producto</div>';
        } else {
          content.innerHTML = '<div style="color:#dc2626">Error al consultar insumos</div>';
        }
        return;
      }
      var d = await r.json();
      var resumen = d.resumen || {};
      var headerColor = resumen.deficit > 0 ? '#dc2626' : resumen.justo > 0 ? '#d97706' : '#16a34a';
      var headerLabel = resumen.deficit > 0 ? '❌ Faltan insumos críticos' : resumen.justo > 0 ? '⚠ Stock justo' : '✅ Listo para producir';
      var html = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e2e8f0">' +
        '<b style="color:'+headerColor+';font-size:13px">'+headerLabel+'</b>' +
        '<span style="font-size:10px;color:#64748b">'+resumen.ok+' OK · '+resumen.justo+' justo · '+resumen.deficit+' déficit · '+resumen.total+' MPs</span>' +
        '</div>';
      // Mostrar primero deficit, luego justo, luego ok
      var orden = {'deficit':0, 'justo':1, 'ok':2};
      var sorted = (d.items||[]).slice().sort(function(a,b){ return (orden[a.status]||9) - (orden[b.status]||9); });
      // Solo mostrar los problemáticos por defecto
      var problematicos = sorted.filter(function(x){ return x.status !== 'ok'; });
      if(!problematicos.length){
        html += '<div style="color:#16a34a;font-size:12px;text-align:center;padding:6px">Todos los '+resumen.total+' MPs disponibles ✓</div>';
      } else {
        html += problematicos.slice(0,8).map(function(it){
          var icon = it.status==='deficit'?'❌':it.status==='justo'?'⚠':'✓';
          var color = it.status==='deficit'?'#dc2626':it.status==='justo'?'#d97706':'#16a34a';
          var fmt = function(g){ return Math.round(g).toLocaleString('es-CO')+' g'; };
          return '<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:11px">' +
            '<span>'+icon+' <b>'+_escHTML(it.nombre)+'</b></span>' +
            '<span style="color:'+color+';font-family:monospace">'+fmt(it.disponible_g)+' / '+fmt(it.requerido_g)+(it.faltante_g>0?' <b>(falta '+fmt(it.faltante_g)+')</b>':'')+'</span>' +
            '</div>';
        }).join('');
        if(problematicos.length > 8){
          html += '<div style="text-align:center;font-size:10px;color:#94a3b8;margin-top:4px">+ '+(problematicos.length-8)+' más</div>';
        }
      }
      content.innerHTML = html;
    }catch(e){
      content.innerHTML = '<div style="color:#dc2626">Error de red</div>';
    }
  }
  function cerrarModalProgramar() {
    document.getElementById('modal-programar').style.display = 'none';
  }
  function actualizarDashboard() {
    cargarProgramacion(null);
  }

  // ── Sub-tabs internos de Programacion ────────────────────────────────────
  function switchProgTab(tab){
    try {
      // Mapeo tab → ID del div objetivo
      var TAB_TO_DIV = {
        'planv2': 'ptab-planv2',
        'asignacion': 'ptab-asignacion',
        'mando': 'ptab-plano',
        'autoplan': 'ptab-autoplan',
        'config': 'ptab-config',
        'maquila': 'ptab-maquila',
        // Compat con flujos viejos
        'presentaciones': 'ptab-presentaciones',
        'equipos': 'ptab-equipos',
        'preflight': 'ptab-preflight',
        'plansem': 'ptab-plansem',
        'conteo': 'ptab-conteo',
        'centro': 'ptab-centro',
        'plan': 'ptab-plan',
        'checklist': 'ptab-checklist',
        'tareas': 'ptab-tareas',
        'plano': 'ptab-plano',
      };
      // Ocultar TODOS los ptab-* dentro de #programacion
      var prog = document.getElementById('programacion');
      if(prog){
        var todos = prog.querySelectorAll('[id^="ptab-"]');
        todos.forEach(function(div){ div.style.display = 'none'; });
      }
      // Mostrar el div objetivo
      var targetId = TAB_TO_DIV[tab];
      if(targetId){
        var elT = document.getElementById(targetId);
        if(elT){
          elT.style.display = 'block';
        } else {
          console.warn('switchProgTab: div '+targetId+' no encontrado');
        }
      }
      // Hooks específicos por tab — cada uno se invoca solo si la función existe
      if(tab==='maquila' && typeof maquilaInit==='function') maquilaInit();
      if(tab==='checklist' && typeof cargarChecklistResumen==='function'){
        cargarChecklistResumen();
        var sel = document.getElementById('ck-autorefresh');
        if(sel && typeof ckSetAutoRefresh==='function') ckSetAutoRefresh(sel.value);
      } else if(typeof ckSetAutoRefresh==='function'){ ckSetAutoRefresh(0); }
      if(tab==='tareas' && typeof cargarTareasOperativas==='function') cargarTareasOperativas();
      if(tab==='plano' || tab==='mando'){
        if(typeof renderCentroMando==='function') renderCentroMando();
        if(typeof cmStartAutoRefresh==='function') cmStartAutoRefresh();
      } else if(typeof cmStopAutoRefresh==='function'){ cmStopAutoRefresh(); }
      if(tab==='presentaciones' && typeof cargarPresentaciones==='function') cargarPresentaciones();
      if(tab==='equipos' && typeof cargarEquipos==='function') cargarEquipos();
      if(tab==='preflight' && typeof cargarPreflightLista==='function') cargarPreflightLista();
      if(tab==='plansem' && typeof cargarPlanSemanal==='function') cargarPlanSemanal();
      if(tab==='autoplan' && typeof apInit==='function') apInit();
      if(tab==='conteo' && typeof cargarConteoCalendario==='function') cargarConteoCalendario();
      if(tab==='plan' && typeof cargarPlanificacion==='function' && !window._planLoaded){
        cargarPlanificacion(60);
      }
      // Estilos botones — los 6 oficiales
      function _bg(id, activeStyle, activeClass){
        var b = document.getElementById(id);
        if(!b) return;
        if(activeClass){ b.style.background = activeStyle; b.style.color='#fff'; b.style.boxShadow='0 3px 10px rgba(0,0,0,.2)'; }
        else { b.style.background='#e2e8f0'; b.style.color='#1a4a7a'; b.style.boxShadow=''; }
      }
      _bg('prog-tab-planv2',     'linear-gradient(135deg,#0f766e,#0891b2)', tab==='planv2');
      _bg('prog-tab-asignacion', '#0f766e',                                  tab==='asignacion');
      _bg('prog-tab-mando',      '#1a4a7a',                                  tab==='mando');
      _bg('prog-tab-autoplan',   'linear-gradient(135deg,#7c3aed,#dc2626)',  tab==='autoplan');
      _bg('prog-tab-maquila',    'linear-gradient(135deg,#1a4a7a,#0891b2)', tab==='maquila');
      _bg('prog-tab-config',     '#1f2937',                                  tab==='config');
      // === Hooks de inicialización para las 4 pestañas oficiales ===
      if(tab==='planv2' && typeof planV2Init==='function') planV2Init();
      if(tab==='asignacion' && typeof asigInit==='function') asigInit();
      if(tab==='config' && typeof cfgInit==='function') cfgInit();
    } catch(err) {
      _toast('Error en switchProgTab: ' + err.message, 0);
    }
  }

  // ── Centro de Mando (Capa 3+ live tracking) ─────────────────────────────
  // Cache global del ultimo payload, sirve para el panel detalle al hacer click
  var _CM_LAST = null;
  var _CM_TIMER = null;

  function cmStartAutoRefresh(){
    if(_CM_TIMER) return;
    var chk = document.getElementById('cm-auto');
    if(!chk || !chk.checked) return;
    _CM_TIMER = setInterval(function(){
      if(document.getElementById('ptab-plano').style.display === 'none'){
        cmStopAutoRefresh(); return;
      }
      var c = document.getElementById('cm-auto');
      if(c && c.checked) renderCentroMando(true /*silent*/);
    }, 30000);
  }
  function cmStopAutoRefresh(){
    if(_CM_TIMER){ clearInterval(_CM_TIMER); _CM_TIMER = null; }
  }

  function _fmtMin(min){
    if(min == null) return '';
    if(min < 60) return min + ' min';
    var h = Math.floor(min/60), m = min%60;
    return h + 'h' + (m?(' '+m+'min'):'');
  }

  async function renderCentroMando(silent){
    var fechaInp = document.getElementById('plano-fecha');
    if(!fechaInp.value){ fechaInp.value = new Date().toISOString().slice(0,10); }
    try{
      var r = await fetch('/api/planta/centro-mando');
      var d = await r.json();
      _CM_LAST = d;
      // Pintar KPIs
      var kpiBox = document.getElementById('cm-kpis');
      var k = d.kpis || {};
      kpiBox.innerHTML = [
        _kpiCard('🟡 Producciones AHORA', k.producciones_activas_ahora||0, k.producciones_activas_ahora>0?'#ca8a04':'#94a3b8'),
        _kpiCard('✅ Terminadas hoy',     k.terminadas_hoy||0,             '#16a34a'),
        _kpiCard('⏱ Cycle time prom',     k.cycle_time_promedio_min!=null?_fmtMin(k.cycle_time_promedio_min):'—', '#0f766e'),
        _kpiCard('🟢 Salas libres',       k.salas_libres||0,               '#16a34a'),
        _kpiCard('🔴 Salas sucias',       k.salas_sucias||0,               k.salas_sucias>0?'#b91c1c':'#94a3b8'),
        _kpiCard('🟡 Salas ocupadas',     k.salas_ocupadas||0,             '#ca8a04'),
      ].join('');
      // Mapa codigo → area
      var mapa = {};
      (d.areas||[]).forEach(function(a){ mapa[a.codigo] = a; });
      // Pintar cada rect
      var ESTADO_COLORS = {
        libre:      {fill:'#86efac', stroke:'#16a34a', txt:'#16a34a'},
        ocupada:    {fill:'#fde68a', stroke:'#ca8a04', txt:'#92400e'},
        sucia:      {fill:'#fca5a5', stroke:'#b91c1c', txt:'#991b1b'},
        limpiando:  {fill:'#93c5fd', stroke:'#1d4ed8', txt:'#1e3a8a'}
      };
      ['PROD1','PROD2','PROD3','PROD4','ENV1','ACOND','ALMP','ALMPT'].forEach(function(cod){
        var g = document.querySelector('[data-codigo="'+cod+'"]');
        if(!g) return;
        var rect = g.querySelector('rect.r');
        var lbl  = g.querySelector('text.status');
        var a    = mapa[cod];
        if(!a) return;
        var estadoVisual = a.estado;
        // si tiene producciones en curso → ocupada
        var enCurso = (a.ocupada_por||[]).filter(function(o){ return o.en_curso; });
        if(enCurso.length) estadoVisual = 'ocupada';
        var col = ESTADO_COLORS[estadoVisual] || ESTADO_COLORS.libre;
        if(rect){
          rect.setAttribute('fill', col.fill);
          rect.setAttribute('stroke', col.stroke);
        }
        if(lbl){
          var txt = estadoVisual.toUpperCase();
          if(enCurso.length){
            var o = enCurso[0];
            var quien = o.operario_elaboracion || o.operario_envasado || o.operario_dispensacion || o.operario_acondicionamiento || '';
            txt = o.producto + (o.minutos_corridos!=null?' · ⏱'+_fmtMin(o.minutos_corridos):'') +
                  (quien?(' · 🧑'+quien.split(' ')[0]):'');
          }
          lbl.textContent = txt;
          lbl.setAttribute('fill', col.txt);
        }
      });
      // Click handler
      document.querySelectorAll('[data-codigo]').forEach(function(g){
        var cod = g.getAttribute('data-codigo');
        if(!mapa[cod]) return;
        g.onclick = function(){ mostrarDetalleSala(mapa[cod]); };
      });
      // Eventos recientes (timeline lateral)
      cargarTimelineEventos(d.eventos_recientes || []);
      cargarRotacionOperarios();
      cargarTablaOperarios();
      cargarKpisActividades();
      var lu = document.getElementById('cm-last-update');
      if(lu) lu.textContent = 'actualizado ' + new Date().toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    }catch(e){
      if(!silent){ _toast('Error al cargar Centro de Mando: '+e.message, 0); }
    }
  }

  function _kpiCard(label, val, color){
    return '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;border-left:4px solid '+color+'">'+
      '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">'+label+'</div>'+
      '<div style="font-size:22px;font-weight:800;color:'+color+';margin-top:2px">'+val+'</div>'+
      '</div>';
  }

  function cargarTimelineEventos(evs){
    var box = document.getElementById('plano-rotacion');
    // En realidad pintaremos timeline + rotacion juntos en cargarRotacionOperarios
    // (rotacion sigue debajo). Aqui guardamos el array y la rotacion lo merge.
    window._CM_EVENTS = evs;
  }

  function mostrarDetalleSala(a){
    var box = document.getElementById('plano-detalle');
    if(!a){ box.style.display='none'; return; }
    box.style.display = 'block';
    var caps = [];
    if(a.puede_producir) caps.push('Producción');
    if(a.puede_envasar)  caps.push('Envasado');
    if(a.marmita_ml)     caps.push('Marmita ' + a.marmita_ml + ' ml');
    if(a.especial)       caps.push('Especial: ' + a.especial);
    if(a.tipo === 'conteo_ciclico') caps.push('Conteos cíclicos');
    if(a.tipo === 'apoyo_asignable') caps.push('Apoyo asignable');
    var ocupHTML = '';
    if(a.ocupada_por && a.ocupada_por.length){
      ocupHTML = '<div style="margin-top:12px"><b>Producciones asignadas / en curso:</b>' +
        a.ocupada_por.map(function(o){
          var ops = [];
          if(o.operario_dispensacion)      ops.push('Disp: '+o.operario_dispensacion);
          if(o.operario_elaboracion)       ops.push('Elab: '+o.operario_elaboracion);
          if(o.operario_envasado)          ops.push('Env: '+o.operario_envasado);
          if(o.operario_acondicionamiento) ops.push('Acon: '+o.operario_acondicionamiento);
          var liveBadge = '';
          if(o.en_curso){
            liveBadge = '<span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;letter-spacing:.5px;margin-left:6px;text-transform:uppercase">EN CURSO ⏱'+_fmtMin(o.minutos_corridos)+'</span>';
          } else if(o.fin_real_at){
            liveBadge = '<span style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px">terminada</span>';
          } else {
            liveBadge = '<span style="background:#94a3b8;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;margin-left:6px">pendiente iniciar</span>';
          }
          // Botones iniciar/terminar
          var btns = '';
          if(!o.inicio_real_at){
            btns = '<button onclick="cmIniciarProduccion('+o.produccion_id+')" style="background:#16a34a;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">▶ Iniciar producción</button>';
          } else if(!o.fin_real_at){
            btns = '<button onclick="cmTerminarProduccion('+o.produccion_id+')" style="background:#dc2626;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">⏹ Terminar producción</button>';
          }
          return '<div style="background:#f8fafc;border-radius:6px;padding:10px 14px;margin-top:8px;border-left:3px solid '+(o.en_curso?'#ca8a04':o.fin_real_at?'#16a34a':'#94a3b8')+'">' +
            '<div><b>'+o.producto+'</b> · '+o.lotes+' lote(s) · '+(o.kg||0)+' kg' + liveBadge + '</div>' +
            (ops.length?'<div style="font-size:11px;color:#64748b;margin-top:4px">'+ops.join(' · ')+'</div>':'') +
            (btns?'<div style="margin-top:8px">'+btns+'</div>':'') +
            '</div>';
        }).join('') + '</div>';
    } else {
      ocupHTML = '<div style="margin-top:10px;color:#16a34a;font-size:13px">✓ Sin producción asignada</div>';
    }
    box.innerHTML =
      '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">'+
        '<h3 style="margin:0;color:#1a4a7a">🏭 '+a.nombre+' <span style="font-size:12px;color:#64748b;font-weight:500">('+a.codigo+')</span></h3>'+
        '<div style="display:flex;gap:6px;flex-wrap:wrap">'+
          ['libre','sucia','limpiando','ocupada'].map(function(est){
            var current = a.estado===est;
            return '<button onclick="cambiarEstadoSala('+a.id+',\\''+est+'\\')" style="padding:5px 10px;border:1px solid '+(current?'#1a4a7a':'#cbd5e1')+';background:'+(current?'#1a4a7a':'#fff')+';color:'+(current?'#fff':'#475569')+';border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;text-transform:uppercase">'+est+'</button>';
          }).join('') +
        '</div>'+
      '</div>'+
      '<div style="font-size:13px;color:#475569;margin-top:8px">'+caps.join(' · ')+'</div>'+
      ocupHTML +
      // Sección turnos de operarios (con timer + iniciar/terminar)
      '<div id="cm-turnos-'+a.id+'" style="margin-top:14px;padding:12px;background:#fefce8;border:1px solid #fde68a;border-radius:8px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">' +
          '<b style="color:#854d0e;font-size:13px">🧑‍🏭 Turnos de operarios en esta sala</b>' +
          '<button onclick="abrirIniciarTurno('+a.id+')" style="background:#16a34a;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">+ Iniciar turno</button>' +
        '</div>' +
        '<div id="cm-turnos-list-'+a.id+'" style="font-size:12px"><div style="color:#94a3b8;text-align:center;padding:10px">Cargando turnos...</div></div>' +
      '</div>';
    cargarTurnosSala(a.id);
  }

  async function cargarTurnosSala(area_id){
    var box = document.getElementById('cm-turnos-list-'+area_id);
    if(!box) return;
    try{
      var r = await fetch('/api/planta/areas/'+area_id+'/actividades');
      var d = await r.json();
      var acts = d.actividades || [];
      var activas = acts.filter(function(x){ return x.en_curso; });
      var cerradas = acts.filter(function(x){ return !x.en_curso; }).slice(0, 5);
      var html = '';
      if(activas.length){
        html += '<div style="margin-bottom:8px"><b style="font-size:11px;color:#854d0e;text-transform:uppercase;letter-spacing:.5px">⏱ En curso ahora</b></div>';
        html += activas.map(function(t){
          var icon = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'}[t.tipo]||'📋';
          return '<div style="background:#fff;border-left:3px solid #ca8a04;padding:8px 10px;margin-bottom:6px;border-radius:0 6px 6px 0;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">' +
            '<div style="flex:1;min-width:140px">' +
              '<div style="font-weight:600;color:#0f172a">'+icon+' <b>'+t.operario_nombre+'</b> · <span style="color:#64748b">'+t.tipo+'</span></div>' +
              (t.descripcion?'<div style="font-size:11px;color:#64748b;margin-top:2px">'+t.descripcion+'</div>':'') +
              '<div style="font-size:11px;color:#ca8a04;font-weight:700;margin-top:3px">⏱ '+_fmtMin(t.minutos_corridos)+' transcurridos</div>' +
            '</div>' +
            '<button onclick="terminarTurno('+t.id+','+area_id+')" style="background:#dc2626;color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:11px;font-weight:700;cursor:pointer">⏹ Terminar</button>' +
          '</div>';
        }).join('');
      } else {
        html += '<div style="color:#94a3b8;text-align:center;padding:6px;font-style:italic">Nadie trabajando ahora — click "+ Iniciar turno"</div>';
      }
      if(cerradas.length){
        html += '<div style="margin-top:10px;padding-top:8px;border-top:1px dashed #fde68a"><b style="font-size:10px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px">Últimos turnos cerrados</b></div>';
        html += cerradas.map(function(t){
          var icon = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'}[t.tipo]||'📋';
          return '<div style="font-size:11px;color:#475569;padding:4px 8px;background:#f8fafc;border-radius:4px;margin-top:3px;display:flex;justify-content:space-between">' +
            '<span>'+icon+' '+t.operario_nombre+' · '+t.tipo+'</span>' +
            '<span style="color:#64748b">⏱ '+_fmtMin(t.duracion_min)+'</span>' +
          '</div>';
        }).join('');
      }
      box.innerHTML = html;
    }catch(e){ box.innerHTML = '<div style="color:#dc2626;font-size:12px">Error al cargar turnos</div>'; }
  }

  async function abrirIniciarTurno(area_id){
    // Cargar operarios para selector
    if(!_PLANTA_OPERARIOS) await _mpCargarCatalogos();
    var ops = (_PLANTA_OPERARIOS||[]).filter(function(o){ return !o.es_jefe; });
    if(!ops.length){ _toast('Sin operarios activos', 0); return; }
    var opSel = ops.map(function(o){ return '<option value="'+o.id+'">'+o.nombre_completo+'</option>'; }).join('');
    var modal = document.getElementById('modal-turno');
    if(!modal){
      modal = document.createElement('div');
      modal.id = 'modal-turno';
      modal.style.cssText = 'display:flex;position:fixed;inset:0;background:rgba(15,23,42,.7);z-index:99999;align-items:center;justify-content:center;padding:20px';
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:20px 22px;max-width:420px;width:100%">' +
        '<h3 style="color:#1a4a7a;font-size:16px;margin-bottom:14px">⏱ Iniciar turno operario</h3>' +
        '<input type="hidden" id="tn-area">' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Operario *</label>' +
        '<select id="tn-op" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">'+opSel+'</select>' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Tipo de actividad *</label>' +
        '<select id="tn-tipo" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">' +
          '<option value="produccion">🏭 Producción</option>' +
          '<option value="dispensacion">⚖ Dispensación</option>' +
          '<option value="envasado">📦 Envasado</option>' +
          '<option value="acondicionamiento">🎁 Acondicionamiento</option>' +
          '<option value="conteo_ciclico">📊 Conteo cíclico</option>' +
          '<option value="limpieza">🧹 Limpieza</option>' +
          '<option value="mantenimiento">🔧 Mantenimiento</option>' +
          '<option value="otro">📋 Otro</option>' +
        '</select>' +
        '<label style="font-size:12px;font-weight:600;color:#475569;display:block;margin-bottom:3px">Descripción (opcional)</label>' +
        '<textarea id="tn-descr" rows="2" placeholder="Ej: lote LBHA-261001, turno A" style="width:100%;padding:7px 9px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;font-family:inherit;margin-bottom:14px"></textarea>' +
        '<div style="display:flex;gap:8px;justify-content:flex-end">' +
          '<button id="tn-cancel" style="background:#e2e8f0;color:#475569;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer">Cancelar</button>' +
          '<button id="tn-save" style="background:#16a34a;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;cursor:pointer">▶ Iniciar</button>' +
        '</div>' +
      '</div>';
      document.body.appendChild(modal);
      document.getElementById('tn-cancel').onclick = function(){
        document.getElementById('modal-turno').style.display='none';
      };
      document.getElementById('tn-save').onclick = iniciarTurno;
    } else {
      document.getElementById('tn-op').innerHTML = opSel;
      modal.style.display = 'flex';
    }
    document.getElementById('tn-area').value = area_id;
    document.getElementById('tn-descr').value = '';
  }

  async function iniciarTurno(){
    var area_id = document.getElementById('tn-area').value;
    var body = {
      operario_id: parseInt(document.getElementById('tn-op').value),
      tipo: document.getElementById('tn-tipo').value,
      descripcion: document.getElementById('tn-descr').value
    };
    try{
      var r = await fetch('/api/planta/areas/'+area_id+'/actividades', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if(d.ok){
        if(d.cerrado_previo){ _toast('Turno previo de '+d.operario+' cerrado en otra sala', 1); }
        else { _toast('Turno iniciado: '+d.operario, 1); }
        document.getElementById('modal-turno').style.display = 'none';
        cargarTurnosSala(area_id);
        renderCentroMando();
      } else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function terminarTurno(act_id, area_id){
    var obs = prompt('Observaciones del turno (opcional):', '');
    if(obs === null) return; // canceló
    try{
      var r = await fetch('/api/planta/actividades/'+act_id+'/terminar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({observaciones: obs || null})
      });
      var d = await r.json();
      if(d.ok){
        _toast('Turno cerrado · ' + (d.duracion_min!=null ? _fmtMin(d.duracion_min) : ''), 1);
        cargarTurnosSala(area_id);
        renderCentroMando();
      } else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function cmIniciarProduccion(id){
    if(!confirm('¿Iniciar la producción ahora? Quedará el contador corriendo.')) return;
    try{
      var r = await fetch('/api/programacion/programar/'+id+'/iniciar', {method:'POST'});
      var d = await r.json();
      if(d.ok){ _toast(d.ya_iniciada?'Ya estaba iniciada':'Producción iniciada · contador en marcha', 1); renderCentroMando(); }
      else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }
  async function cmTerminarProduccion(id){
    if(!confirm('¿Terminar la producción? La sala quedará en estado SUCIA esperando limpieza.')) return;
    try{
      var r = await fetch('/api/programacion/programar/'+id+'/terminar', {method:'POST'});
      var d = await r.json();
      if(d.ok){
        var msg = d.ya_terminada ? 'Ya estaba terminada' : ('Producción terminada · cycle time: '+_fmtMin(d.cycle_time_min));
        _toast(msg, 1);
        renderCentroMando();
      }
      else { _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function cambiarEstadoSala(id, nuevo){
    try{
      var r = await fetch('/api/planta/areas/'+id+'/estado', {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado: nuevo})
      });
      var d = await r.json();
      if(d.ok){
        _toast('Sala actualizada: '+nuevo, 1);
        renderCentroMando();
      } else {
        _toast('Error: '+(d.error||'desconocido'), 0);
      }
    }catch(e){ _toast('Error de red', 0); }
  }

  // ── Gestion de operarios CRUD ────────────────────────────────────────
  async function cargarTablaOperarios(){
    var box = document.getElementById('crew-mgmt-tabla');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/operarios?incluir_inactivos=1');
      var d = await r.json();
      var ops = d.operarios || [];
      if(!ops.length){
        box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Sin operarios. Click "+ Nuevo operario".</div>';
        return;
      }
      var html = '<table style="width:100%;border-collapse:collapse;font-size:13px">' +
        '<thead><tr style="text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0;background:#f8fafc">' +
        '<th style="padding:8px">Nombre</th>' +
        '<th style="padding:8px">Rol predeterminado</th>' +
        '<th style="padding:8px;text-align:center">Flags</th>' +
        '<th style="padding:8px;text-align:center">Estado</th>' +
        '<th style="padding:8px;text-align:right">Acciones</th>' +
        '</tr></thead><tbody>';
      ops.forEach(function(o){
        var flags = [];
        if(o.fija_dispensacion) flags.push('🔒 fijo dispensación');
        if(o.es_jefe) flags.push('⭐ jefe');
        var estado = o.activo
          ? '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">ACTIVO</span>'
          : '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700">INACTIVO</span>';
        var btnDelOrEnable = o.activo
          ? '<button onclick="desactivarOperario('+o.id+',&quot;'+o.nombre_completo.replace(/"/g,'&quot;')+'&quot;)" style="background:#fee2e2;color:#991b1b;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">Desactivar</button>'
          : '<button onclick="reactivarOperario('+o.id+')" style="background:#d1fae5;color:#065f46;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">Reactivar</button>';
        html += '<tr style="border-bottom:1px solid #f1f5f9">' +
          '<td style="padding:8px;font-weight:600">'+_escHTML(o.nombre_completo)+'</td>' +
          '<td style="padding:8px;color:#475569">'+_escHTML(o.rol||'todero')+'</td>' +
          '<td style="padding:8px;text-align:center;font-size:11px;color:#64748b">'+(flags.join(' · ')||'—')+'</td>' +
          '<td style="padding:8px;text-align:center">'+estado+'</td>' +
          '<td style="padding:8px;text-align:right">' +
            '<button onclick="abrirModalEditarOperario('+o.id+')" style="background:#dbeafe;color:#1e40af;border:none;padding:5px 9px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;margin-right:4px">Editar</button>' +
            btnDelOrEnable +
          '</td>' +
        '</tr>';
      });
      html += '</tbody></table>';
      box.innerHTML = html;
    }catch(e){ box.innerHTML = '<div style="color:#dc2626">Error al cargar.</div>'; }
  }

  function abrirModalNuevoOperario(){
    document.getElementById('op-modal-title').textContent = 'Nuevo operario';
    document.getElementById('op-id').value = '';
    document.getElementById('op-nombre').value = '';
    document.getElementById('op-apellido').value = '';
    document.getElementById('op-rol').value = 'todero';
    document.getElementById('op-fija').checked = false;
    document.getElementById('op-jefe').checked = false;
    document.getElementById('modal-operario').style.display = 'flex';
  }

  async function abrirModalEditarOperario(id){
    try{
      var r = await fetch('/api/planta/operarios?incluir_inactivos=1');
      var d = await r.json();
      var op = (d.operarios||[]).find(function(o){ return o.id === id; });
      if(!op){ _toast('No encontrado', 0); return; }
      document.getElementById('op-modal-title').textContent = 'Editar: '+op.nombre_completo;
      document.getElementById('op-id').value = op.id;
      document.getElementById('op-nombre').value = op.nombre;
      document.getElementById('op-apellido').value = op.apellido;
      document.getElementById('op-rol').value = op.rol || 'todero';
      document.getElementById('op-fija').checked = !!op.fija_dispensacion;
      document.getElementById('op-jefe').checked = !!op.es_jefe;
      document.getElementById('modal-operario').style.display = 'flex';
    }catch(e){ _toast('Error de red', 0); }
  }

  function cerrarModalOperario(){
    document.getElementById('modal-operario').style.display = 'none';
  }

  async function guardarOperario(){
    var id = document.getElementById('op-id').value;
    var body = {
      nombre: document.getElementById('op-nombre').value.trim(),
      apellido: document.getElementById('op-apellido').value.trim(),
      rol_predeterminado: document.getElementById('op-rol').value,
      fija_en_dispensacion: document.getElementById('op-fija').checked,
      es_jefe_produccion: document.getElementById('op-jefe').checked
    };
    if(!body.nombre){ _toast('Nombre requerido', 0); return; }
    try{
      var url = id ? '/api/planta/operarios/'+id : '/api/planta/operarios';
      var method = id ? 'PATCH' : 'POST';
      var r = await fetch(url, {method:method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
      var d = await r.json();
      if(d.ok){
        _toast(id?'Operario actualizado':'Operario creado', 1);
        cerrarModalOperario();
        cargarTablaOperarios();
        // Limpiar cache para que el próximo "Programar" lo incluya
        _PLANTA_OPERARIOS = null;
      }else{ _toast('Error: '+(d.error||'?'), 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function desactivarOperario(id, nombre){
    if(!confirm('¿Desactivar a '+nombre+'? No aparecerá en selectores nuevos pero el historial se preserva.')) return;
    try{
      var r = await fetch('/api/planta/operarios/'+id, {method:'DELETE'});
      var d = await r.json();
      if(d.ok){ _toast('Desactivado', 1); cargarTablaOperarios(); _PLANTA_OPERARIOS=null; }
      else { _toast('Error', 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  async function reactivarOperario(id){
    try{
      var r = await fetch('/api/planta/operarios/'+id, {
        method:'PATCH', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({activo: true})
      });
      var d = await r.json();
      if(d.ok){ _toast('Reactivado', 1); cargarTablaOperarios(); _PLANTA_OPERARIOS=null; }
      else { _toast('Error', 0); }
    }catch(e){ _toast('Error de red', 0); }
  }

  // Toggle del checkbox auto-refresh
  document.addEventListener('DOMContentLoaded', function(){
    var chk = document.getElementById('cm-auto');
    if(chk){ chk.addEventListener('change', function(){
      if(this.checked) cmStartAutoRefresh();
      else cmStopAutoRefresh();
    });}
    // Default tab: Plan v2 cuando abres Programación
    setTimeout(function(){
      if(typeof switchProgTab==='function') switchProgTab('planv2');
    }, 100);
  });

  // KPIs de actividades (turnos, horas por operario, por tipo)
  async function cargarKpisActividades(){
    var box = document.getElementById('cm-act-kpis');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/actividades/kpis');
      var d = await r.json();
      var op = d.por_operario || [];
      var tp = d.por_tipo || [];
      var html = '';
      // Card resumen turnos activos ahora
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px">' +
          '<b style="color:#1a4a7a;font-size:14px">⏱ Turnos operarios</b>' +
          '<span style="font-size:11px;color:#64748b">📅 ' + (d.desde||'') + ' → ' + (d.hasta||'') + ' · Activos ahora: <b style="color:'+(d.turnos_activos_ahora>0?'#ca8a04':'#94a3b8')+'">' + (d.turnos_activos_ahora||0) + '</b></span>' +
        '</div>';
      if(op.length){
        html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px"><div>';
        html += '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Por operario</div>';
        html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
        op.forEach(function(o){
          var hrs = o.horas;
          var bar = Math.min(100, Math.round(hrs * 5));  // visual rough scale
          html += '<tr style="border-bottom:1px solid #f1f5f9">' +
            '<td style="padding:4px 0;font-weight:600">'+_escHTML(o.operario)+'</td>' +
            '<td style="padding:4px 0;color:#64748b;text-align:right">'+o.turnos+' turno'+(o.turnos===1?'':'s')+'</td>' +
            '<td style="padding:4px 0;text-align:right;font-weight:700;color:#0f766e">'+hrs+'h</td>' +
            '</tr>';
        });
        html += '</table></div><div>';
        html += '<div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Por tipo de actividad</div>';
        html += '<table style="width:100%;font-size:12px;border-collapse:collapse">';
        var iconos = {produccion:'🏭',dispensacion:'⚖',envasado:'📦',acondicionamiento:'🎁',conteo_ciclico:'📊',limpieza:'🧹',mantenimiento:'🔧',otro:'📋'};
        tp.forEach(function(t){
          html += '<tr style="border-bottom:1px solid #f1f5f9">' +
            '<td style="padding:4px 0">'+(iconos[t.tipo]||'📋')+' '+t.tipo+'</td>' +
            '<td style="padding:4px 0;color:#64748b;text-align:right">'+t.turnos+' turno'+(t.turnos===1?'':'s')+'</td>' +
            '<td style="padding:4px 0;text-align:right;font-weight:700;color:#0f766e">'+t.horas+'h</td>' +
            '</tr>';
        });
        html += '</table></div></div>';
      } else {
        html += '<div style="text-align:center;color:#94a3b8;padding:20px;font-size:13px;font-style:italic">' +
          'Aún sin turnos cerrados en los últimos 30 días — inicia un turno desde cualquier sala para empezar a medir.' +
          '</div>';
      }
      html += '</div>';
      box.innerHTML = html;
    }catch(e){ box.innerHTML = ''; }
  }

  // Capa 4: rotación operarios — pinta panel debajo del plano
  async function cargarRotacionOperarios(){
    var box = document.getElementById('plano-rotacion');
    if(!box) return;
    try{
      var r = await fetch('/api/planta/operarios/historial');
      var d = await r.json();
      var ops = d.operarios || [];
      if(!ops.length){
        box.innerHTML = '';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px">' +
        '<h3 style="margin:0 0 10px;color:#1a4a7a;font-size:15px">👥 Rotación de operarios <span style="font-size:11px;color:#64748b;font-weight:500">(últimos '+(d.ventana_dias||14)+' días)</span></h3>' +
        '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead>' +
          '<tr style="text-align:left;color:#64748b;border-bottom:1px solid #e2e8f0">' +
            '<th style="padding:6px 4px">Operario</th>' +
            '<th style="padding:6px 4px;text-align:center">Disp</th>' +
            '<th style="padding:6px 4px;text-align:center">Elab</th>' +
            '<th style="padding:6px 4px;text-align:center">Env</th>' +
            '<th style="padding:6px 4px;text-align:center">Acon</th>' +
            '<th style="padding:6px 4px">Sugerencia</th>' +
          '</tr></thead><tbody>';
      ops.forEach(function(op){
        var f = op.fases || {};
        var rotar = op.sugerir_rotar
          ? '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:8px;font-weight:700">⚠ rotar — '+op.dias_en_fase+' días en '+op.fase_acumulada+'</span>'
          : '<span style="color:#16a34a">✓ ok</span>';
        function _cell(n){ return '<td style="padding:6px 4px;text-align:center;color:'+(n?'#0f172a':'#cbd5e1')+';font-weight:'+(n?'700':'400')+'">'+(n||0)+'</td>'; }
        html += '<tr style="border-bottom:1px solid #f1f5f9"><td style="padding:6px 4px;font-weight:600">'+op.nombre+' '+(op.apellido||'')+'</td>' +
          _cell(f.dispensacion) + _cell(f.elaboracion) + _cell(f.envasado) + _cell(f.acondicionamiento) +
          '<td style="padding:6px 4px">'+rotar+'</td></tr>';
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    }catch(e){
      box.innerHTML = '';
    }
  }

  async function cargarTareasOperativas(){
    var lista = document.getElementById('tareas-op-lista');
    if(!lista) return;
    lista.innerHTML = '<div style="color:#94a3b8;text-align:center;padding:20px">Cargando...</div>';
    try {
      // Sebastian (29-abr-2026): /planta solo muestra tareas fisicas de planta
      // (excluye chat_asignacion como "Cargar influencers" que era para Jeferson).
      var r = await fetch('/api/tareas-operativas?contexto=planta');
      var d = await r.json();
      var tareas = d.tareas || [];
      var badge = document.getElementById('prog-tareas-badge');
      if(badge){
        var pend = tareas.filter(function(t){return t.estado==='pendiente'||t.estado==='en_progreso'}).length;
        if(pend){ badge.textContent = pend; badge.style.display='inline-block'; }
        else badge.style.display = 'none';
      }
      if(!tareas.length){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px;font-size:13px">Sin tareas operativas pendientes 🎉</div>';
        return;
      }
      lista.innerHTML = tareas.map(function(t){
        var tipoColors = {sacar_envases_serigrafia:'#7c3aed',sacar_envases_tampografia:'#7c3aed',sacar_inventario:'#16a34a',envasado:'#0891b2',etiquetado:'#d97706',general:'#64748b'};
        var col = tipoColors[t.tipo]||'#64748b';
        var estCol = t.estado==='pendiente'?'#dc2626':t.estado==='en_progreso'?'#d97706':t.estado==='completada'?'#15803d':'#94a3b8';
        var fechaObj = t.fecha_objetivo?'<span style="color:#dc2626;font-size:11px;font-weight:700">📅 '+_escHTML(t.fecha_objetivo)+'</span>':'';
        return '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+col+';border-radius:10px;padding:14px 18px;margin-bottom:10px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center">'+
          '<div>'+
            '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'+
              '<span style="font-weight:700;color:#0f172a;font-size:14px">'+_escHTML(t.titulo)+'</span>'+
              '<span style="background:'+col+'22;color:'+col+';font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px">'+_escHTML(t.tipo||'')+'</span>'+
              '<span style="background:'+estCol+'22;color:'+estCol+';font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;text-transform:uppercase">'+_escHTML(t.estado)+'</span>'+
            '</div>'+
            '<div style="font-size:13px;color:#475569;margin-top:6px">'+_escHTML(t.descripcion||'')+'</div>'+
            '<div style="font-size:11px;color:#64748b;margin-top:4px">'+
              (t.producto_relacionado?'📦 <b>'+_escHTML(t.producto_relacionado)+'</b> · ':'')+
              (t.cantidad>0?'🔢 '+Math.round(t.cantidad).toLocaleString('es-CO')+' und · ':'')+
              (t.asignado_a?'👥 '+_escHTML(t.asignado_a)+' · ':'')+
              fechaObj +
            '</div>'+
          '</div>'+
          '<div style="text-align:right">'+
            (t.estado==='pendiente'||t.estado==='en_progreso' ? '<button onclick="completarTareaOp('+t.id+')" style="background:#16a34a;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer">✓ Completar</button>' : '') +
          '</div>'+
        '</div>';
      }).join('');
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function completarTareaOp(tid){
    var obs = prompt('Observaciones del cierre (opcional):', '') || '';
    try {
      var r = await fetch('/api/tareas-operativas/'+tid+'/completar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({observaciones: obs})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      _toast('Tarea completada', 1);
      cargarTareasOperativas();
    } catch(e){ alert('Error: '+e.message); }
  }

  // ── Fase 0: Presentaciones por Producto ──────────────────────────────
  // Sebastian + Alejandro (30-abr-2026): suero 30/15/10mL, contornos 15/10mL,
  // maxlash 4.5mL, blush 6g. Sin esto, planear "produzcamos para 2 meses"
  // es ambiguo. UI lista + crea + aplica plantillas por categoría.
  var _presProductos = [];

  async function cargarPresentaciones(){
    var lista = document.getElementById('pres-lista');
    var kpis  = document.getElementById('pres-kpis');
    var banner= document.getElementById('pres-cobertura-banner');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r1 = await fetch('/api/planta/presentaciones');
      var d1 = await r1.json();
      var r2 = await fetch('/api/planta/presentaciones/productos-disponibles');
      var d2 = await r2.json();
      _presProductos = d2.productos || [];

      // KPIs
      var totalPres = (d1.presentaciones||[]).length;
      var totalProd = _presProductos.length;
      var prodConPres = _presProductos.filter(function(p){return (p.n_presentaciones||0)>0}).length;
      var sinPres = totalProd - prodConPres;
      var pct = totalProd ? Math.round(prodConPres/totalProd*100) : 0;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Productos en BD</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+totalProd+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Con presentación</div><div style="font-size:24px;font-weight:800;color:#15803d">'+prodConPres+' <span style="font-size:13px;color:#64748b">('+pct+'%)</span></div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Sin presentación</div><div style="font-size:24px;font-weight:800;color:'+(sinPres?'#dc2626':'#15803d')+'">'+sinPres+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Total presentaciones</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+totalPres+'</div></div>';

      if(sinPres > 0){
        banner.style.display = 'block';
        banner.innerHTML = '⚠ Hay <b>'+sinPres+' productos sin presentación</b> definida. Sin esto el sistema no puede sugerir tamaño de lote correcto. Usa "Aplicar plantilla" o "+ Nueva presentación" para completarlos.';
      } else {
        banner.style.display = 'none';
      }

      // Lista agrupada por producto
      if(!totalProd){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">No hay productos en formula_headers</div>';
        return;
      }
      var byProd = d1.por_producto || {};
      var html = '';
      _presProductos.forEach(function(prod){
        var pres = byProd[prod.producto_nombre] || [];
        var color = pres.length ? '#15803d' : '#dc2626';
        var status = pres.length ? '✓ '+pres.length+' presentación'+(pres.length>1?'es':'') : '⚠ sin presentación';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:10px;padding:14px 16px">'
          +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
          +'<div><b style="color:#0f172a">'+_escHTML(prod.producto_nombre)+'</b> <span style="color:#64748b;font-size:12px;margin-left:6px">lote '+(prod.lote_size_kg||0)+' kg</span></div>'
          +'<div style="font-size:12px;color:'+color+';font-weight:700">'+status+'</div>'
          +'</div>';
        if(pres.length){
          html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">';
          pres.forEach(function(p){
            var vol = p.volumen_ml ? p.volumen_ml+' mL' : (p.peso_g ? p.peso_g+' g' : '');
            html += '<div style="background:#f0fdf4;border:1px solid #86efac;color:#166534;padding:6px 10px;border-radius:6px;font-size:12px;display:flex;align-items:center;gap:6px">'
              +'<b>'+_escHTML(p.etiqueta)+'</b>'
              +(vol?'<span style="color:#64748b">·</span><span>'+vol+'</span>':'')
              +(p.envase_codigo?'<span style="color:#64748b">·</span><span style="font-family:monospace;font-size:11px">'+_escHTML(p.envase_codigo)+'</span>':'')
              +' <button onclick="eliminarPresentacion('+p.id+')" title="Eliminar" style="background:transparent;border:none;color:#dc2626;cursor:pointer;font-weight:700;padding:0 2px">×</button>'
              +'</div>';
          });
          html += '</div>';
        } else {
          html += '<div style="margin-top:8px;display:flex;gap:6px"><button onclick="abrirAplicarPlantilla(\\''+_escAttr(prod.producto_nombre)+'\\')" style="background:#1a4a7a;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">🏭 Plantilla</button>'
            +'<button onclick="abrirNuevaPresentacion(\\''+_escAttr(prod.producto_nombre)+'\\')" style="background:#0f766e;color:#fff;border:none;padding:5px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Manual</button></div>';
        }
        html += '</div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function _escAttr(s){ return (s==null?'':String(s)).replace(/'/g, "&#39;").replace(/"/g, '&quot;'); }

  function _llenarSelectProductos(selId, valorPreset){
    var sel = document.getElementById(selId);
    if(!sel) return;
    sel.innerHTML = '<option value="">— elegir producto —</option>'
      + _presProductos.map(function(p){
        var sel = (p.producto_nombre===valorPreset) ? ' selected' : '';
        return '<option value="'+_escAttr(p.producto_nombre)+'"'+sel+'>'+_escHTML(p.producto_nombre)+'</option>';
      }).join('');
  }

  function abrirNuevaPresentacion(productoPreset){
    _llenarSelectProductos('pres-producto', productoPreset||'');
    ['pres-categoria','pres-codigo','pres-etiqueta','pres-volumen','pres-peso','pres-envase','pres-sku','pres-notas'].forEach(function(id){
      var el = document.getElementById(id); if(el) el.value = '';
    });
    var m = document.getElementById('modal-pres-nueva');
    m.style.display = 'flex';
  }
  function cerrarPresModal(){ document.getElementById('modal-pres-nueva').style.display='none'; }

  async function guardarPresentacion(){
    var body = {
      producto_nombre: (document.getElementById('pres-producto').value||'').trim(),
      categoria: (document.getElementById('pres-categoria').value||'').trim(),
      presentacion_codigo: (document.getElementById('pres-codigo').value||'').trim(),
      etiqueta: (document.getElementById('pres-etiqueta').value||'').trim(),
      volumen_ml: parseFloat(document.getElementById('pres-volumen').value)||null,
      peso_g: parseFloat(document.getElementById('pres-peso').value)||null,
      envase_codigo: (document.getElementById('pres-envase').value||'').trim(),
      sku_shopify: (document.getElementById('pres-sku').value||'').trim(),
      notas: (document.getElementById('pres-notas').value||'').trim(),
    };
    if(!body.producto_nombre){ alert('Producto requerido'); return; }
    if(!body.presentacion_codigo){ alert('Código de presentación requerido'); return; }
    if(!body.etiqueta){ alert('Etiqueta requerida'); return; }
    try {
      var r = await fetch('/api/planta/presentaciones', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cerrarPresModal();
      _toast('Presentación creada', 1);
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  function abrirAplicarPlantilla(productoPreset){
    _llenarSelectProductos('plt-producto', productoPreset||'');
    document.getElementById('plt-categoria').value = '';
    document.getElementById('modal-pres-plantilla').style.display = 'flex';
  }
  function cerrarPlantillaModal(){ document.getElementById('modal-pres-plantilla').style.display='none'; }

  async function aplicarPlantilla(){
    var prod = (document.getElementById('plt-producto').value||'').trim();
    var cat  = (document.getElementById('plt-categoria').value||'').trim();
    if(!prod || !cat){ alert('Producto y categoría requeridos'); return; }
    try {
      var r = await fetch('/api/planta/presentaciones/bulk-categoria', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod, categoria: cat})
      });
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cerrarPlantillaModal();
      _toast('Plantilla aplicada · '+(d.total||0)+' presentaciones creadas', 1);
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  async function eliminarPresentacion(pid){
    if(!confirm('¿Eliminar (desactivar) esta presentación?')) return;
    try {
      var r = await fetch('/api/planta/presentaciones/'+pid, {method:'DELETE'});
      var d = await r.json().catch(function(){return {};});
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      cargarPresentaciones();
    } catch(e){ alert('Error de red: '+e.message); }
  }

  // ── Fase 1: Equipos del Excel + sugerir-área ─────────────────────────
  var _eqTodos = [];
  var _eqTipos = {};
  var _eqAreas = {};

  async function cargarEquipos(){
    var lista = document.getElementById('eq-lista');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/planta/equipos');
      var d = await r.json();
      _eqTodos = d.equipos || [];
      _eqTipos = d.por_tipo || {};
      // Por area
      var porArea = d.por_area || {};
      _eqAreas = porArea;

      // KPIs
      var kpis = document.getElementById('eq-kpis');
      var nTanques = _eqTodos.filter(function(e){return e.tipo==='tanque'||e.tipo==='marmita'||e.tipo==='olla'}).length;
      var nEnvas   = _eqTodos.filter(function(e){return e.tipo==='envasadora'||e.tipo==='tapadora'}).length;
      var nMedida  = _eqTodos.filter(function(e){return ['balanza','bascula','viscosimetro','phmetro','espectrofotometro','termometro','termohigrometro','pie_de_rey','picnometro','pesa_patron'].indexOf(e.tipo)>=0}).length;
      var nMezcla  = _eqTodos.filter(function(e){return ['agitador','homogenizador','mezclador','batidor','molino','plancha'].indexOf(e.tipo)>=0}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+_eqTodos.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Tanques/marmitas</div><div style="font-size:24px;font-weight:800;color:#1a4a7a">'+nTanques+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Envasado</div><div style="font-size:24px;font-weight:800;color:#0891b2">'+nEnvas+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Mezcla</div><div style="font-size:24px;font-weight:800;color:#7c3aed">'+nMezcla+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Medición/CC</div><div style="font-size:24px;font-weight:800;color:#16a34a">'+nMedida+'</div></div>';

      // Llenar selects de filtro
      var selT = document.getElementById('eq-filtro-tipo');
      var selA = document.getElementById('eq-filtro-area');
      var tiposSorted = Object.keys(_eqTipos).sort();
      selT.innerHTML = '<option value="">Todos los tipos ('+_eqTodos.length+')</option>'
        + tiposSorted.map(function(t){ return '<option value="'+t+'">'+t+' ('+_eqTipos[t]+')</option>'; }).join('');
      var areasSorted = Object.keys(porArea).sort();
      selA.innerHTML = '<option value="">Todas las áreas</option>'
        + areasSorted.map(function(a){ return '<option value="'+a+'">'+a+' ('+(porArea[a].length)+')</option>'; }).join('');

      filtrarEquipos();
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function filtrarEquipos(){
    var lista = document.getElementById('eq-lista');
    var q = (document.getElementById('eq-search').value||'').toLowerCase();
    var ft = (document.getElementById('eq-filtro-tipo').value||'').toLowerCase();
    var fa = (document.getElementById('eq-filtro-area').value||'');
    var filtered = _eqTodos.filter(function(e){
      if(ft && (e.tipo||'').toLowerCase()!==ft) return false;
      if(fa && (e.area_codigo||'')!==fa) return false;
      if(q){
        var t = ((e.codigo||'')+' '+(e.nombre||'')+' '+(e.capacidad_raw||'')+' '+(e.area_codigo||'')+' '+(e.ubicacion_raw||'')).toLowerCase();
        if(t.indexOf(q)<0) return false;
      }
      return true;
    });
    if(!filtered.length){
      lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">Sin resultados.</div>';
      return;
    }
    // Agrupar por area
    var grupos = {};
    filtered.forEach(function(e){
      var a = e.area_codigo || '—';
      grupos[a] = grupos[a] || [];
      grupos[a].push(e);
    });
    var html = '';
    Object.keys(grupos).sort().forEach(function(a){
      var eqs = grupos[a];
      html += '<div style="margin-bottom:14px"><h3 style="margin:0 0 8px;color:#1a4a7a;font-size:14px">'+a+' <span style="color:#64748b;font-size:11px;font-weight:500">('+eqs.length+' equipos)</span></h3>'
        +'<table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><thead><tr style="background:#f1f5f9"><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Código</th><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Nombre</th><th style="padding:8px 12px;text-align:left;font-size:11px;color:#475569;text-transform:uppercase">Tipo</th><th style="padding:8px 12px;text-align:right;font-size:11px;color:#475569;text-transform:uppercase">Capacidad</th></tr></thead><tbody>';
      eqs.forEach(function(e){
        var capStr = e.capacidad_raw || '—';
        if(e.capacidad_litros){ capStr = e.capacidad_litros+' L'; }
        else if(e.capacidad_kg){ capStr = e.capacidad_kg+' kg'; }
        html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:7px 12px;font-family:monospace;font-size:12px;color:#1e293b">'+_escHTML(e.codigo)+'</td><td style="padding:7px 12px;font-size:13px">'+_escHTML(e.nombre||'')+'</td><td style="padding:7px 12px;font-size:11px"><span style="background:#ede9fe;color:#5b21b6;padding:2px 7px;border-radius:8px;font-weight:600">'+_escHTML(e.tipo||'otro')+'</span></td><td style="padding:7px 12px;font-size:12px;text-align:right;color:#0f172a;font-weight:600">'+_escHTML(capStr)+'</td></tr>';
      });
      html += '</tbody></table></div>';
    });
    lista.innerHTML = html;
  }

  function abrirSugerirArea(){
    document.getElementById('sa-producto').value = '';
    document.getElementById('sa-lote').value = '';
    document.getElementById('sa-resultado').innerHTML = '';
    document.getElementById('modal-sugerir-area').style.display = 'flex';
  }
  function cerrarSugerirArea(){ document.getElementById('modal-sugerir-area').style.display='none'; }

  async function ejecutarSugerirArea(){
    var prod = (document.getElementById('sa-producto').value||'').trim() || 'Producto X';
    var lote = parseFloat(document.getElementById('sa-lote').value);
    if(!lote || lote<=0){ alert('Tamaño de lote requerido (kg)'); return; }
    var box = document.getElementById('sa-resultado');
    box.innerHTML = '<div style="color:#94a3b8;padding:14px;text-align:center">Calculando...</div>';
    try {
      var r = await fetch('/api/planta/sugerir-area', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto_nombre: prod, lote_kg: lote})
      });
      var d = await r.json();
      if(!r.ok){ box.innerHTML='<div style="color:#dc2626;padding:14px">'+(d.error||'Error')+'</div>'; return; }
      var sugerencias = d.sugerencias||[];
      var html = '<div style="background:#f8fafc;border:1px solid #e2e8f0;padding:10px 14px;border-radius:6px;margin-bottom:10px;font-size:12px;color:#475569">📊 '+_escHTML(d.mensaje)+'</div>';
      if(!sugerencias.length){
        box.innerHTML = html;
        return;
      }
      sugerencias.forEach(function(s, i){
        var medal = i===0 ? '🥇' : i===1 ? '🥈' : i===2 ? '🥉' : '·';
        var color = i===0 ? '#15803d' : '#64748b';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:8px;padding:12px 14px;margin-bottom:8px">'
          +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:6px">'
          +'<div><b style="color:#0f172a;font-size:14px">'+medal+' '+_escHTML(s.area_nombre)+'</b> <span style="font-family:monospace;color:#64748b;font-size:11px">('+_escHTML(s.area_codigo)+')</span></div>'
          +'<div style="font-size:13px;font-weight:700;color:'+color+'">Score '+s.score+'</div>'
          +'</div>'
          +'<div style="margin-top:6px;font-size:12px;color:#475569">🛢 '+_escHTML(s.tanque.tanque_nombre)+' <span style="color:#64748b">('+_escHTML(s.tanque.tanque_codigo)+')</span> · '+s.tanque.capacidad_litros+'L · uso '+s.utilizacion_pct+'%</div>'
          +(s.envasado_sugerido?'<div style="margin-top:4px;font-size:11px;color:#0891b2">📦 Envasado sugerido: '+s.envasado_sugerido+'</div>':'')
          +'<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px">'
          +(s.razones||[]).map(function(r){ return '<span style="background:#f1f5f9;color:#475569;font-size:11px;padding:2px 8px;border-radius:8px">'+_escHTML(r)+'</span>'; }).join('')
          +'</div></div>';
      });
      box.innerHTML = html;
    } catch(e){ box.innerHTML='<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
  }

  // ── Fase 2: Pre-flight (motor de gates) ──────────────────────────────
  // Sebastian (30-abr-2026): "programado un producto dice donde como, le dice
  // inteligentemente area sucia confirmar limpieza confirmar tal y tal cosa".
  async function cargarPreflightLista(){
    var lista = document.getElementById('pf-lista');
    var kpis  = document.getElementById('pf-kpis');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando producciones próximas...</div>';
    try {
      // Reusar /api/programar para obtener producciones próximas
      var r = await fetch('/api/programacion/programar?dias=14');
      var d = await r.json();
      var eventos = d.eventos || d.items || [];
      // Filtrar las que tienen produccion_id (de produccion_programada local)
      var producciones = eventos.filter(function(e){return e.id && e.estado!=='completado' && e.estado!=='cancelado'});

      // Para cada produccion, llamar a /preflight (paralelo limit 5)
      var conGates = [];
      for(var i=0;i<producciones.length;i+=5){
        var batch = producciones.slice(i, i+5);
        var res = await Promise.all(batch.map(function(p){
          return fetch('/api/planta/preflight/'+p.id).then(function(r){return r.json()}).catch(function(){return null});
        }));
        res.forEach(function(pf, idx){
          if(pf && pf.gates) conGates.push(Object.assign({}, batch[idx], {preflight: pf}));
        });
      }

      // KPIs
      var nListos = conGates.filter(function(p){return p.preflight.listo && p.preflight.resumen.warn===0}).length;
      var nWarn   = conGates.filter(function(p){return p.preflight.listo && p.preflight.resumen.warn>0}).length;
      var nBlock  = conGates.filter(function(p){return !p.preflight.listo}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #6b7280;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total programadas</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+conGates.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Listas para iniciar</div><div style="font-size:24px;font-weight:800;color:#15803d">'+nListos+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Con advertencias</div><div style="font-size:24px;font-weight:800;color:#d97706">'+nWarn+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #dc2626;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Bloqueadas</div><div style="font-size:24px;font-weight:800;color:#dc2626">'+nBlock+'</div></div>';

      if(!conGates.length){
        lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;background:#f8fafc;border-radius:10px">Sin producciones programadas próximas (14d).</div>';
        return;
      }

      var html = '';
      conGates.forEach(function(p){
        var pf = p.preflight;
        var color = pf.resumen.blocker>0 ? '#dc2626' : (pf.resumen.warn>0 ? '#d97706' : '#15803d');
        var badge = pf.resumen.blocker>0 ? '⛔ BLOQUEADA' : (pf.resumen.warn>0 ? '⚠ Con advertencias' : '✅ LISTA');
        html += '<div onclick="abrirPreflightModal('+p.id+')" style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+color+';border-radius:10px;padding:14px 18px;margin-bottom:10px;cursor:pointer;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center" onmouseover="this.style.background=\\'#f8fafc\\'" onmouseout="this.style.background=\\'#fff\\'">'
          +'<div>'
          +'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><b style="color:#0f172a;font-size:14px">'+_escHTML(p.titulo||p.producto||'Producción '+p.id)+'</b>'
          +'<span style="background:'+color+'22;color:'+color+';font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px">'+badge+'</span></div>'
          +'<div style="font-size:12px;color:#64748b;margin-top:4px">📅 '+_escHTML(p.fecha_inicio||p.fecha_programada||'')+(p.lotes?' · '+p.lotes+' lote(s)':'')+'</div>'
          +'<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">'
          +pf.gates.map(function(g){
            var col = g.status==='blocker'?'#dc2626':(g.status==='warn'?'#d97706':'#15803d');
            var ic  = g.status==='blocker'?'⛔':(g.status==='warn'?'⚠':'✓');
            return '<span style="background:'+col+'18;color:'+col+';padding:3px 8px;border-radius:6px;font-size:11px;font-weight:600">'+ic+' '+_escHTML(g.titulo)+'</span>';
          }).join('')
          +'</div></div>'
          +'<div style="text-align:right;color:'+color+';font-size:24px">→</div>'
          +'</div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function abrirPreflightModal(prodId){
    var modal = document.getElementById('modal-preflight');
    var hdr = document.getElementById('pf-modal-header');
    var body = document.getElementById('pf-modal-gates');
    hdr.innerHTML = '<div style="color:#94a3b8">Cargando...</div>';
    body.innerHTML = '';
    modal.style.display = 'flex';
    try {
      var r = await fetch('/api/planta/preflight/'+prodId);
      var pf = await r.json();
      var color = pf.resumen.blocker>0?'#dc2626':(pf.resumen.warn>0?'#d97706':'#15803d');
      hdr.innerHTML = '<div style="margin-bottom:14px">'
        +'<h3 style="margin:0 0 4px;color:'+color+';font-size:16px">'+_escHTML(pf.veredicto)+'</h3>'
        +'<div style="font-size:13px;color:#475569"><b>'+_escHTML(pf.producto||'')+'</b> · '+(pf.lotes||1)+' lote(s) · 📅 '+_escHTML(pf.fecha_programada||'')+'</div>'
        +'<div style="font-size:11px;color:#64748b;margin-top:4px">Producción ID '+pf.produccion_id+' · estado: '+_escHTML(pf.estado||'')+'</div>'
        +'</div>';
      body.innerHTML = pf.gates.map(function(g){
        var col = g.status==='blocker'?'#dc2626':(g.status==='warn'?'#d97706':'#15803d');
        var bg  = g.status==='blocker'?'#fef2f2':(g.status==='warn'?'#fffbeb':'#f0fdf4');
        var ic  = g.status==='blocker'?'⛔':(g.status==='warn'?'⚠':'✅');
        var meta = '';
        if(g.meta && g.meta.deficit){
          meta = '<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#475569">'
            + g.meta.deficit.map(function(m){ return '<li>'+_escHTML(m.nombre)+': falta '+m.faltante_g+'g</li>'; }).join('')
            + '</ul>';
        } else if(g.meta && g.meta.items){
          meta = '<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;color:#475569">'
            + g.meta.items.map(function(it){
                var s = it.stock!=null ? ' · stock '+it.stock : '';
                return '<li>'+_escHTML(it.presentacion)+(it.envase?' · '+_escHTML(it.envase):'')+s+'</li>';
              }).join('')
            + '</ul>';
        }
        var btn = '';
        if(g.accion === 'confirmar_limpieza'){
          btn = '<button onclick="confirmarLimpiezaPF('+prodId+')" style="margin-top:8px;background:'+col+';color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">🧹 Confirmar limpieza profunda</button>';
        } else if(g.accion === 'asignar_area'){
          btn = '<div style="margin-top:8px;font-size:11px;color:#64748b">→ Ve a Centro de Mando para asignar área</div>';
        } else if(g.accion === 'crear_tareas_compra'){
          btn = '<div style="margin-top:8px;font-size:11px;color:#64748b">→ Catalina puede ver el déficit en /compras</div>';
        }
        return '<div style="background:'+bg+';border:1px solid '+col+'33;border-left:4px solid '+col+';border-radius:8px;padding:12px 14px;margin-bottom:8px">'
          +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:6px">'
          +'<div><b style="color:'+col+'">'+ic+' '+_escHTML(g.titulo)+'</b><div style="font-size:12px;color:#475569;margin-top:2px">'+_escHTML(g.mensaje||'')+'</div></div>'
          +'<span style="font-family:monospace;color:#94a3b8;font-size:10px">'+_escHTML(g.gate)+'</span>'
          +'</div>'
          + meta + btn
          +'</div>';
      }).join('');
    } catch(e){
      body.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }
  function cerrarPreflightModal(){ document.getElementById('modal-preflight').style.display='none'; }

  async function confirmarLimpiezaPF(prodId){
    var nota = prompt('Nota de la limpieza (opcional):', '');
    if(nota===null) return;
    try {
      var r = await fetch('/api/planta/preflight/'+prodId+'/confirmar-limpieza', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({nota: nota||''})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      _toast('Limpieza profunda registrada', 1);
      // Refrescar el modal
      abrirPreflightModal(prodId);
    } catch(e){ alert('Error: '+e.message); }
  }

  // ── Fase 4: Plan Semanal con flujo guiado completo ───────────────────
  // Sebastian (30-abr-2026): "tenemos algo maravilloso allí en planta...
  // entonces lo selecciona le sale con la foto, y de una sale señalar
  // envases, solicitar etiquetas, armado de goteros si requiere, aceptar
  // producción se dispone para realizar, entonces automáticamente pasa a
  // que el sistema decida en que área se hace y genere todo".
  var _PS_DATA = null;

  async function cargarPlanSemanal(){
    var grid = document.getElementById('ps-grid');
    var kpis = document.getElementById('ps-kpis');
    var alertasBox = document.getElementById('ps-alertas');
    if(!grid) return;
    var dias = (document.getElementById('ps-dias')||{value:14}).value;
    grid.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px;grid-column:1/-1">Cargando plan semanal...</div>';
    try {
      var r = await fetch('/api/planta/plan-semanal?dias='+dias);
      var d = await r.json();
      _PS_DATA = d;
      // KPIs
      var k = d.kpis || {};
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Producciones</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_roja_dias?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;10</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_roja_dias?'#dc2626':'#15803d')+'">'+(k.alerta_roja_dias||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_amarilla_dias?'#d97706':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;20</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_amarilla_dias?'#d97706':'#15803d')+'">'+(k.alerta_amarilla_dias||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.sin_mp_suficiente?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Sin MP suficiente</div><div style="font-size:26px;font-weight:800;color:'+(k.sin_mp_suficiente?'#dc2626':'#15803d')+'">'+(k.sin_mp_suficiente||0)+'</div></div>';

      // Banner de alertas críticas
      var critic = (d.items||[]).filter(function(it){return it.alerta_dias==='rojo' || !it.alcanza_mp});
      if(critic.length){
        alertasBox.style.display = 'block';
        alertasBox.innerHTML = '<b>⚠ '+critic.length+' producción(es) con alerta crítica:</b><br>'
          + critic.slice(0,5).map(function(c){
            var ico = !c.alcanza_mp ? '🔴 sin MP' : '⏰ '+c.dias_inventario+'d';
            return '· <b>'+_escHTML(c.producto)+'</b> ('+_escHTML(c.fecha_programada)+') '+ico;
          }).join('<br>');
      } else {
        alertasBox.style.display = 'none';
      }

      // Cards
      var items = d.items || [];
      if(!items.length){
        grid.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:40px;grid-column:1/-1;background:#f8fafc;border-radius:10px">Sin producciones programadas en el rango.</div>';
        return;
      }
      grid.innerHTML = items.map(function(it){
        var diasCol = it.alerta_dias==='rojo' ? '#dc2626' : (it.alerta_dias==='amarillo'?'#d97706':(it.alerta_dias==='verde'?'#15803d':'#94a3b8'));
        var diasTxt = it.dias_inventario===null ? '—' : it.dias_inventario+'d';
        var mpCol = it.alcanza_mp ? '#15803d' : '#dc2626';
        var mpTxt = it.alcanza_mp ? '✓ MP listas' : '✗ Faltan '+(it.mp_deficit||[]).length+' MP';
        var img = it.imagen_url
          ? '<img src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:120px;object-fit:cover;border-radius:8px 8px 0 0" alt="">'
          : '<div style="width:100%;height:120px;background:linear-gradient(135deg,#1a4a7a,#0891b2);border-radius:8px 8px 0 0;display:flex;align-items:center;justify-content:center;color:#fff;font-size:36px">📦</div>';
        var pres = (it.presentaciones||[]).slice(0,2).map(function(p){
          return '<span style="background:#f0f9ff;color:#0369a1;padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600">'+_escHTML(p.etiqueta)+'</span>';
        }).join(' ');
        return '<div onclick="abrirPlanSemModal('+it.produccion_id+')" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .12s,box-shadow .12s" onmouseover="this.style.transform=\\'translateY(-2px)\\';this.style.boxShadow=\\'0 8px 20px rgba(0,0,0,.1)\\'" onmouseout="this.style.transform=\\'\\';this.style.boxShadow=\\'\\'">'
          + img
          +'<div style="padding:12px 14px">'
          +'<div style="font-weight:800;color:#0f172a;font-size:14px;margin-bottom:4px">'+_escHTML(it.producto)+'</div>'
          +'<div style="font-size:12px;color:#64748b;margin-bottom:8px">📅 '+_escHTML(it.fecha_programada)+' · '+(it.lotes||1)+' lote(s) · '+(it.lote_size_kg||0)+'kg</div>'
          +'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">'+pres+'</div>'
          +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px">'
          +'<div style="background:'+diasCol+'15;border:1px solid '+diasCol+'40;color:'+diasCol+';padding:6px 8px;border-radius:6px;text-align:center;font-size:11px;font-weight:700">⏰ '+diasTxt+'</div>'
          +'<div style="background:'+mpCol+'15;border:1px solid '+mpCol+'40;color:'+mpCol+';padding:6px 8px;border-radius:6px;text-align:center;font-size:11px;font-weight:700">'+mpTxt+'</div>'
          +'</div>'
          +(it.area_nombre?'<div style="font-size:11px;color:#64748b">🏭 '+_escHTML(it.area_nombre)+'</div>':'<div style="font-size:11px;color:#dc2626;font-weight:600">⚠ Sin área asignada</div>')
          +'</div></div>';
      }).join('');
    } catch(e){
      grid.innerHTML = '<div style="color:#dc2626;padding:14px;grid-column:1/-1">Error: '+e.message+'</div>';
    }
  }

  function abrirPlanSemModal(prodId){
    if(!_PS_DATA) return;
    var item = (_PS_DATA.items||[]).find(function(x){return x.produccion_id===prodId});
    if(!item) return;
    var modal = document.getElementById('modal-plansem');
    var box = document.getElementById('ps-modal-content');
    var diasCol = item.alerta_dias==='rojo' ? '#dc2626' : (item.alerta_dias==='amarillo'?'#d97706':(item.alerta_dias==='verde'?'#15803d':'#94a3b8'));
    var img = item.imagen_url
      ? '<img src="'+_escAttr(item.imagen_url)+'" style="width:100%;height:200px;object-fit:cover" alt="">'
      : '<div style="width:100%;height:200px;background:linear-gradient(135deg,#1a4a7a,#0891b2);display:flex;align-items:center;justify-content:center;color:#fff;font-size:80px">📦</div>';

    var mpHtml = '';
    if(item.mp_status && item.mp_status.length){
      mpHtml = '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px"><thead><tr style="background:#f1f5f9"><th style="padding:6px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">MP</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Req</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Stock</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Reservado</th><th style="padding:6px 10px;text-align:right;font-size:10px;color:#475569">Neto</th></tr></thead><tbody>';
      item.mp_status.forEach(function(m){
        var c = m.estado==='ok'?'#15803d':(m.estado==='justo'?'#d97706':'#dc2626');
        mpHtml += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:5px 10px"><span style="color:'+c+';font-weight:700">'+(m.estado==='ok'?'✓':m.estado==='justo'?'⚠':'✗')+'</span> '+_escHTML(m.material_nombre)+'</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace">'+m.requerido_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;color:#64748b">'+m.stock_total_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;color:#94a3b8">-'+m.reservado_previo_g.toLocaleString()+'g</td>'
          +'<td style="padding:5px 10px;text-align:right;font-family:monospace;font-weight:700;color:'+c+'">'+m.disponible_neto_g.toLocaleString()+'g</td></tr>';
      });
      mpHtml += '</tbody></table>';
    }

    var presOptions = '<option value="">— elegir presentación —</option>'
      + (item.presentaciones||[]).map(function(p){
        var vol = p.volumen_ml?p.volumen_ml+' mL':(p.peso_g?p.peso_g+' g':'');
        return '<option value="'+p.id+'">'+_escHTML(p.etiqueta)+(vol?' · '+vol:'')+'</option>';
      }).join('');

    box.innerHTML = img
      +'<div style="padding:18px 22px">'
      +'<div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px;margin-bottom:14px">'
      +'<div><h2 style="margin:0;color:#0f172a;font-size:20px">'+_escHTML(item.producto)+'</h2><div style="font-size:13px;color:#64748b;margin-top:2px">📅 '+_escHTML(item.fecha_programada)+' · '+(item.lotes||1)+' lote(s) de '+(item.lote_size_kg||0)+'kg</div></div>'
      +'<button onclick="cerrarPlanSemModal()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button>'
      +'</div>'
      // Estado actual
      +'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">'
      +'<div style="background:'+diasCol+'15;border:1px solid '+diasCol+'40;border-radius:8px;padding:10px"><div style="font-size:10px;color:'+diasCol+';text-transform:uppercase;font-weight:700">Días inventario</div><div style="font-size:20px;font-weight:800;color:'+diasCol+';margin-top:2px">'+(item.dias_inventario===null?'—':item.dias_inventario+'d')+'</div></div>'
      +'<div style="background:'+(item.alcanza_mp?'#f0fdf4':'#fef2f2')+';border:1px solid '+(item.alcanza_mp?'#86efac':'#fecaca')+';border-radius:8px;padding:10px"><div style="font-size:10px;color:'+(item.alcanza_mp?'#15803d':'#dc2626')+';text-transform:uppercase;font-weight:700">MP</div><div style="font-size:14px;font-weight:800;color:'+(item.alcanza_mp?'#15803d':'#dc2626')+';margin-top:2px">'+(item.alcanza_mp?'✓ Alcanzan':'✗ Faltan '+(item.mp_deficit||[]).length)+'</div></div>'
      +'<div style="background:'+(item.area_nombre?'#f1f5f9':'#fef3c7')+';border:1px solid '+(item.area_nombre?'#cbd5e1':'#fbbf24')+';border-radius:8px;padding:10px"><div style="font-size:10px;color:'+(item.area_nombre?'#475569':'#92400e')+';text-transform:uppercase;font-weight:700">Área</div><div style="font-size:14px;font-weight:800;color:'+(item.area_nombre?'#0f172a':'#92400e')+';margin-top:2px">'+(item.area_nombre||'⚠ Sin asignar')+'</div></div>'
      +'</div>'
      // MP detalle
      +'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:14px">'
      +'<h4 style="margin:0 0 4px;color:#0f172a;font-size:13px">📊 Materias Primas (consumo agregado)</h4>'
      +'<p style="font-size:11px;color:#64748b;margin:0 0 4px">"Reservado" = MP comprometido por producciones programadas ANTES de esta. Neto = lo que realmente queda.</p>'
      + mpHtml
      +'</div>'
      // Presentación + Aceptar
      +'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;margin-bottom:8px">'
      +'<h4 style="margin:0 0 10px;color:#166534;font-size:14px">✅ Aceptar y disparar producción</h4>'
      +'<p style="margin:0 0 10px;font-size:12px;color:#475569">Al aceptar, el sistema:<br>· asigna área (si no la tiene)<br>· crea tareas: señalar envases, solicitar etiquetas'+(item.presentaciones&&item.presentaciones.length?', armar goteros (si aplica)':'')+'<br>· programa envasado mañana<br>· notifica a Calidad para muestra micro</p>'
      +'<label style="font-size:11px;color:#64748b;font-weight:600">Presentación a producir</label>'
      +'<select id="ps-pres" style="width:100%;padding:8px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">'+presOptions+'</select>'
      +'<button onclick="aceptarProduccion('+item.produccion_id+')" style="width:100%;background:#15803d;color:#fff;border:none;padding:12px;border-radius:8px;font-size:14px;font-weight:800;cursor:pointer">✅ ACEPTAR PRODUCCIÓN</button>'
      +'</div>'
      +'<div id="ps-resultado"></div>'
      +'</div>';
    modal.style.display = 'flex';
  }
  function cerrarPlanSemModal(){ document.getElementById('modal-plansem').style.display='none'; }

  async function aceptarProduccion(prodId){
    var presSel = document.getElementById('ps-pres');
    var presId = presSel ? parseInt(presSel.value) : null;
    var resBox = document.getElementById('ps-resultado');
    resBox.innerHTML = '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;text-align:center;color:#64748b;margin-top:10px">Disparando cascade...</div>';
    try {
      var r = await fetch('/api/planta/aceptar-produccion/'+prodId, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({presentacion_id: presId})
      });
      var d = await r.json();
      if(!r.ok){ resBox.innerHTML='<div style="color:#dc2626;padding:14px;background:#fef2f2;border-radius:8px;margin-top:10px">'+(d.error||'Error')+'</div>'; return; }
      resBox.innerHTML = '<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:14px;margin-top:10px">'
        +'<h4 style="margin:0 0 8px;color:#166534">✅ Producción aceptada</h4>'
        +'<ul style="margin:0;padding-left:18px;font-size:12px;color:#1e293b">'
        + (d.log||[]).map(function(l){ return '<li>'+_escHTML(l)+'</li>'; }).join('')
        + '</ul>'
        +'<div style="margin-top:8px;font-size:12px;color:#64748b">Envasado tentativo: <b>'+_escHTML(d.fecha_envasado_estimada)+'</b> · '+(d.tareas_creadas||[]).length+' tarea(s) creada(s)</div>'
        +'<div style="margin-top:10px"><a href="#" onclick="cerrarPlanSemModal();switchProgTab(\\'preflight\\');return false" style="color:#0891b2;font-weight:700;text-decoration:none">→ Ver Pre-flight</a> · <a href="#" onclick="cerrarPlanSemModal();switchProgTab(\\'tareas\\');return false" style="color:#0891b2;font-weight:700;text-decoration:none">→ Ver Tareas operativas</a></div>'
        +'</div>';
      // Refrescar plan después de unos segundos
      setTimeout(cargarPlanSemanal, 2000);
    } catch(e){ resBox.innerHTML='<div style="color:#dc2626;padding:14px;margin-top:10px">Error de red: '+e.message+'</div>'; }
  }

  // ════════════════════════════════════════════════════════════════════════
  // Conteo Cíclico ABC · Ma/Ju
  // ════════════════════════════════════════════════════════════════════════
  async function cargarConteoCalendario(){
    var lista = document.getElementById('cc-lista');
    var kpis  = document.getElementById('cc-kpis');
    if(!lista) return;
    lista.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/conteo-ciclico/calendario?dias=30');
      var d = await r.json();
      var items = d.items || [];
      var pend = d.pendientes || 0;
      var contados = items.filter(function(x){return x.estado==='cerrado'}).length;
      var conDif = items.filter(function(x){return x.estado==='con_diferencia'}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0f766e;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total programados</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+items.length+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Pendientes</div><div style="font-size:26px;font-weight:800;color:#d97706">'+pend+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Contados OK</div><div style="font-size:26px;font-weight:800;color:#15803d">'+contados+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(conDif?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Con diferencia</div><div style="font-size:26px;font-weight:800;color:'+(conDif?'#dc2626':'#15803d')+'">'+conDif+'</div></div>';

      if(!items.length){
        lista.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;color:#92400e;padding:20px;border-radius:10px;text-align:center">⚠ Sin conteos programados. Ejecuta "🔥 Auto-Plan AHORA" en la pestaña 🤖 Auto-Plan para generar el calendario de conteos.</div>';
        return;
      }
      // Agrupar por fecha
      var porFecha = {};
      items.forEach(function(it){ porFecha[it.fecha] = porFecha[it.fecha] || []; porFecha[it.fecha].push(it); });
      var html = '';
      Object.keys(porFecha).sort().forEach(function(fecha){
        var dia = new Date(fecha+'T00:00:00').toLocaleDateString('es-CO', {weekday:'long', day:'numeric', month:'short'});
        html += '<div style="margin-bottom:14px"><h3 style="margin:0 0 8px;color:#0f766e;font-size:14px;text-transform:capitalize">📅 '+_escHTML(dia)+'</h3>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">ABC</th>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Asignado</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Diferencia</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Acción</th>'
          +'</tr></thead><tbody>';
        porFecha[fecha].forEach(function(it){
          var abcCol = it.categoria_abc==='A' ? '#dc2626' : (it.categoria_abc==='B' ? '#d97706' : '#15803d');
          var estCol = it.estado==='cerrado' ? '#15803d' : (it.estado==='con_diferencia' ? '#dc2626' : '#94a3b8');
          var dif = it.diferencia_g!==null ? (it.diferencia_g>=0?'+':'')+it.diferencia_g.toFixed(0)+'g' : '—';
          html += '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(it.material_nombre||it.material_id)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+abcCol+'22;color:'+abcCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+_escHTML(it.categoria_abc||'C')+'</span></td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(it.asignado_a||'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+estCol+'22;color:'+estCol+';padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700;text-transform:uppercase">'+_escHTML(it.estado||'')+'</span></td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+(it.estado==='con_diferencia'?'#dc2626':'#0f172a')+';font-weight:700">'+_escHTML(dif)+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'
            +(it.estado==='programado' ? '<button onclick="ccAbrirRegistro('+it.id+',\\''+_escAttr(it.material_nombre||it.material_id)+'\\')" style="background:#0f766e;color:#fff;border:none;padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer">📝 Registrar</button>' : '<span style="color:#94a3b8;font-size:11px">'+(it.terminado_por||'—')+'</span>')
            +'</td></tr>';
        });
        html += '</tbody></table></div></div>';
      });
      lista.innerHTML = html;
    } catch(e){
      lista.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function ccAbrirRegistro(id, nombre){
    document.getElementById('cc-reg-id').value = id;
    document.getElementById('cc-reg-titulo').textContent = '📋 Conteo: '+nombre;
    document.getElementById('cc-reg-stock').value = '';
    document.getElementById('cc-reg-notas').value = '';
    document.getElementById('modal-cc-reg').style.display = 'flex';
    setTimeout(function(){document.getElementById('cc-reg-stock').focus();}, 50);
  }

  async function ccRegistrar(){
    var id = document.getElementById('cc-reg-id').value;
    var stock = parseFloat(document.getElementById('cc-reg-stock').value);
    if(isNaN(stock) || stock < 0){ alert('Stock real requerido (gramos)'); return; }
    try {
      var r = await fetch('/api/conteo-ciclico/'+id+'/registrar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({stock_real_g: stock, notas: document.getElementById('cc-reg-notas').value})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      document.getElementById('modal-cc-reg').style.display = 'none';
      var msg = 'Conteo registrado · diferencia '+d.diferencia_g.toFixed(0)+'g ('+d.pct_diferencia+'%)';
      _toast(msg, 1);
      cargarConteoCalendario();
    } catch(e){ alert('Error: '+e.message); }
  }

  // ════════════════════════════════════════════════════════════════════════
  // Auto-Plan Maestro · Sebastian: "la herramienta más avanzada del mundo"
  // Cron L-V 7am · genera producciones + compras + conteos + emails
  // ════════════════════════════════════════════════════════════════════════
  var _AP_SUBTAB = 'resumen';
  var _AP_PLAN = null;

  function apInit(){
    apSwitchSubtab(_AP_SUBTAB);
    apCronStateRefresh();
  }

  async function apCronStateRefresh(){
    try {
      var r = await fetch('/api/auto-plan/cron/state');
      var d = await r.json();
      var span = document.getElementById('ap-cron-status');
      var btn = document.getElementById('ap-cron-toggle-btn');
      if(d.habilitado){
        span.innerHTML = '✓ <b>ACTIVO</b>'+(d.ultima_ejecucion_at?' · última: '+_escHTML(d.ultima_ejecucion_at.substring(0,16)):'');
        btn.textContent = 'Desactivar';
        btn.style.background = '#fee2e2';
        btn.style.color = '#dc2626';
      } else {
        span.innerHTML = '⏸ inactivo';
        btn.textContent = 'Activar';
        btn.style.background = '#fff';
        btn.style.color = '#7c3aed';
      }
    } catch(e){}
  }
  async function apCronToggle(){
    try {
      var sr = await fetch('/api/auto-plan/cron/state');
      var st = await sr.json();
      var nuevo = !st.habilitado;
      var msg = nuevo
        ? '¿ACTIVAR cron diario? Cada L-V 7am el sistema generará plan + SOLs + emails automáticamente.'
        : '¿DESACTIVAR cron? El plan dejará de ejecutarse automáticamente (puedes seguir disparándolo manual con "🔥 Ejecutar AHORA").';
      if(!confirm(msg)) return;
      var r = await fetch('/api/auto-plan/cron/toggle', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({habilitar: nuevo})
      });
      var d = await r.json();
      if(!r.ok){ alert(d.error||'Error'); return; }
      _toast('Cron '+(nuevo?'activado ✓':'desactivado'), 1);
      apCronStateRefresh();
    } catch(e){ alert('Error: '+e.message); }
  }

  function apSwitchSubtab(t){
    _AP_SUBTAB = t;
    ['resumen','skus','mp','emails','aprendizaje','runs'].forEach(function(s){
      var div = document.getElementById('ap-sub-'+s);
      var btn = document.getElementById('ap-stab-'+s);
      if(div) div.style.display = (s===t) ? 'block' : 'none';
      if(btn){
        if(s==='aprendizaje'){
          btn.style.background = (s===t) ? '#dc2626' : 'linear-gradient(135deg,#fbbf24,#dc2626)';
          btn.style.color = '#fff';
        } else {
          btn.style.background = (s===t) ? '#7c3aed' : '#e2e8f0';
          btn.style.color      = (s===t) ? '#fff' : '#475569';
        }
      }
    });
    if(t==='skus') apCargarSkus();
    if(t==='mp') apCargarMp();
    if(t==='emails') apCargarEmails();
    if(t==='runs') apCargarRuns();
    if(t==='aprendizaje') apAnalizarHistorico();
  }

  // 🧠 Aprendizaje del histórico
  async function apAnalizarHistorico(){
    var box = document.getElementById('ap-aprendizaje-content');
    box.style.padding = '20px';
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:30px">🧠 Analizando histórico de 12 meses...</div>';
    try {
      var r = await fetch('/api/auto-plan/aprender-historico?meses_atras=12');
      var d = await r.json();
      var k = d.kpis || {};
      var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px">'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Productos con histórico</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.productos_con_historico||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Productos NUEVOS</div><div style="font-size:26px;font-weight:800;color:#d97706">'+(k.productos_nuevos_sin_historico||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #dc2626;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Recomendaciones</div><div style="font-size:26px;font-weight:800;color:#dc2626">'+(k.recomendaciones_actualizar||0)+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Lotes analizados</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.total_lotes_analizados||0)+'</div></div>'
        +'</div>';

      var aprend = d.aprendizaje || [];
      if(aprend.length){
        html += '<h3 style="color:#0f172a;margin:14px 0 8px">📊 Cadencias detectadas vs configuradas</h3>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lotes hist.</th>'
          +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Última prod.</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia REAL</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Configurada</th>'
          +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Diferencia</th>'
          +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Acción</th>'
          +'</tr></thead><tbody>';
        aprend.forEach(function(a){
          var rowBg = a.recomendar_actualizar ? '#fef3c7' : '#fff';
          var difCol = !a.diferencia_dias ? '#94a3b8' : (Math.abs(a.diferencia_dias)>14?'#dc2626':(Math.abs(a.diferencia_dias)>7?'#d97706':'#15803d'));
          html += '<tr style="border-top:1px solid #f1f5f9;background:'+rowBg+'">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(a.producto)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace">'+a.lotes_historicos+'</td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(a.ultima_produccion||'—')+(a.dias_desde_ultima!=null?' (hace '+a.dias_desde_ultima+'d)':'')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(a.cadencia_real_dias?a.cadencia_real_dias+'d':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:#64748b">'+(a.cadencia_configurada?a.cadencia_configurada+'d':'auto')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+difCol+';font-weight:700">'+(a.diferencia_dias!=null?(a.diferencia_dias>0?'+':'')+a.diferencia_dias+'d':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'+(a.recomendar_actualizar
              ? '<button onclick="apAplicarUna(\\''+_escAttr(a.producto)+'\\','+a.cadencia_real_dias+')" style="background:#15803d;color:#fff;border:none;padding:4px 10px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✓ Adoptar</button>'
              : '<span style="color:#94a3b8;font-size:11px">OK</span>')+'</td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }

      var nuevos = d.productos_nuevos || [];
      if(nuevos.length){
        html += '<h3 style="color:#0f172a;margin:18px 0 8px">🆕 Productos nuevos (sin histórico)</h3>';
        html += '<p style="color:#64748b;font-size:12px;margin:0 0 8px">Estos productos están en formula_headers pero NUNCA se han producido. El sistema los pondrá como "primer lote" en el plan.</p>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;font-size:12px">';
        nuevos.forEach(function(p){
          html += '<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9">'
            +'<span><b>'+_escHTML(p.producto)+'</b> · lote '+(p.lote_kg||0)+'kg</span>'
            +'<span style="color:#d97706;font-size:11px">→ '+_escHTML(p.sugerencia||'producir pronto')+'</span>'
            +'</div>';
        });
        html += '</div>';
      }

      box.style.padding = '0';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  async function apAplicarUna(producto, cadencia){
    if(!confirm('¿Adoptar cadencia REAL de '+cadencia+'d para "'+producto+'"?')) return;
    try {
      var r = await fetch('/api/auto-plan/aplicar-aprendizaje', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({productos:[{producto: producto, cadencia_real_dias: cadencia}]})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Cadencia adoptada', 1);
      apAnalizarHistorico();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apAplicarAprendizaje(){
    if(!confirm('¿Aplicar TODAS las recomendaciones de cadencia detectadas del histórico?\\n\\nLas cadencias actualmente configuradas serán reemplazadas con las REALES.')) return;
    try {
      var r = await fetch('/api/auto-plan/aplicar-aprendizaje', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ '+d.total+' cadencias actualizadas', 1);
      apAnalizarHistorico();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apPreview(){
    var content = document.getElementById('ap-resumen-content');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#7c3aed">🤖 Generando plan...</div>';
    try {
      var r = await fetch('/api/auto-plan/preview?dias=60');
      var d = await r.json();
      _AP_PLAN = d;
      apRenderPlan(d, false);
    } catch(e){
      content.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  async function apEjecutar(){
    if(!confirm('¿Ejecutar Auto-Plan AHORA?\\n\\nEl sistema CREARÁ producciones, SOLs de compra y conteos cíclicos según las cadencias y stock actual. Si hay emails configurados, los enviará.')) return;
    var content = document.getElementById('ap-resumen-content');
    content.innerHTML = '<div style="text-align:center;padding:40px;color:#dc2626">🔥 Ejecutando auto-plan + creando registros...</div>';
    try {
      var r = await fetch('/api/auto-plan/aplicar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({dias: 60})
      });
      var d = await r.json();
      if(!r.ok){ content.innerHTML='<div style="color:#dc2626;padding:20px">'+(d.error||'Error')+'</div>'; return; }
      var banner = document.getElementById('ap-status-banner');
      banner.style.display='block';
      banner.style.background = '#f0fdf4';
      banner.style.border = '1px solid #86efac';
      banner.style.color = '#166534';
      banner.innerHTML = '<b>✅ Auto-Plan aplicado</b> · '
        +(d.resultado.producciones_creadas||[]).length+' producciones creadas · '
        +(d.resultado.compras_creadas||[]).length+' SOLs creadas · '
        +(d.resultado.conteos_creados||[]).length+' conteos programados';
      // Cargar el plan completo para mostrar
      apRenderPlan({
        producciones_propuestas: d.plan.producciones_propuestas,
        compras_propuestas: d.plan.compras_propuestas,
        conteos_propuestos: d.plan.conteos_propuestos,
        alertas: d.plan.alertas,
        log: d.plan.log,
      }, true);
    } catch(e){
      content.innerHTML='<div style="color:#dc2626;padding:20px">Error de red: '+e.message+'</div>';
    }
  }

  function apRenderPlan(d, aplicado){
    var content = document.getElementById('ap-resumen-content');
    content.style.padding = '0';
    content.style.textAlign = 'left';
    content.style.color = 'inherit';
    var prods = d.producciones_propuestas || [];
    var compras = d.compras_propuestas || [];
    var conteos = d.conteos_propuestos || [];
    var alertas = d.alertas || [];

    // KPIs
    var nCrit = alertas.filter(function(a){return a.severidad==='critica'}).length;
    var html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px">'
      +'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:10px;padding:14px"><div style="font-size:11px;color:#166534;text-transform:uppercase;font-weight:700">Producciones</div><div style="font-size:30px;font-weight:800;color:#15803d">'+prods.length+'</div></div>'
      +'<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:10px;padding:14px"><div style="font-size:11px;color:#92400e;text-transform:uppercase;font-weight:700">SOLs auto</div><div style="font-size:30px;font-weight:800;color:#92400e">'+compras.length+'</div></div>'
      +'<div style="background:'+(nCrit?'#fef2f2':'#f0fdf4')+';border:1px solid '+(nCrit?'#fecaca':'#86efac')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:'+(nCrit?'#7f1d1d':'#166534')+';text-transform:uppercase;font-weight:700">Alertas críticas</div><div style="font-size:30px;font-weight:800;color:'+(nCrit?'#dc2626':'#15803d')+'">'+nCrit+'</div></div>'
      +'<div style="background:#f3e8ff;border:1px solid #d8b4fe;border-radius:10px;padding:14px"><div style="font-size:11px;color:#6b21a8;text-transform:uppercase;font-weight:700">Conteos cíclicos</div><div style="font-size:30px;font-weight:800;color:#7c3aed">'+conteos.length+'</div></div>'
      +'</div>';

    // Alertas críticas
    if(alertas.length){
      html += '<h3 style="color:#0f172a;margin:0 0 8px;font-size:14px">⚠ Alertas</h3>';
      html += alertas.map(function(a){
        var c = a.severidad==='critica' ? '#dc2626' : '#d97706';
        return '<div style="background:'+c+'15;border-left:3px solid '+c+';padding:10px 14px;border-radius:6px;margin-bottom:6px;font-size:13px"><b style="color:'+c+'">'+_escHTML(a.titulo||'')+'</b></div>';
      }).join('');
    }

    // Producciones
    html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">📅 Producciones propuestas ('+prods.length+')</h3>';
    if(!prods.length){
      html += '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">Sin producciones nuevas — todo dentro de cobertura ✓</div>';
    } else {
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th><th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Razón</th></tr></thead><tbody>';
      prods.forEach(function(p){
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 10px;font-family:monospace">'+_escHTML(p.fecha_programada)+'</td><td style="padding:7px 10px"><b>'+_escHTML(p.producto)+'</b><br><span style="color:#64748b;font-size:10px">cad '+(p.razon||'')+'</span></td><td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(p.kg_con_merma||0).toFixed(0)+'kg</td><td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.razon||'')+'</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    // Compras
    html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">🛒 Compras automáticas ('+compras.length+')</h3>';
    if(!compras.length){
      html += '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">Sin compras nuevas — MP suficientes</div>';
    } else {
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th><th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cantidad</th><th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Origen</th><th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Urgencia</th></tr></thead><tbody>';
      compras.forEach(function(c){
        var urgCol = c.urgencia==='critica'?'#dc2626':(c.urgencia==='alta'?'#d97706':'#0891b2');
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 10px"><b>'+_escHTML(c.material_nombre)+'</b></td><td style="padding:7px 10px;text-align:right;font-family:monospace">'+(c.cantidad_a_pedir_g/1000).toFixed(2)+'kg</td><td style="padding:7px 10px;font-size:11px">'+_escHTML(c.origen)+' · '+c.lead_time_dias+'d</td><td style="padding:7px 10px;text-align:center"><span style="background:'+urgCol+';color:#fff;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:700">'+c.urgencia.toUpperCase()+'</span></td></tr>';
      });
      html += '</tbody></table></div>';
    }

    // Conteos cíclicos
    if(conteos.length){
      html += '<h3 style="color:#0f172a;margin:18px 0 8px;font-size:14px">📋 Conteos cíclicos (Ma/Ju)</h3>';
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:12px">'
        + conteos.slice(0,10).map(function(c){
          return '<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f1f5f9"><span><b>'+_escHTML(c.fecha)+'</b> · '+_escHTML(c.material_nombre||'')+' <span style="background:#ede9fe;color:#5b21b6;padding:1px 6px;border-radius:6px;font-size:10px">'+_escHTML(c.categoria_abc||'C')+'</span></span><span style="color:#64748b;font-size:10px">'+_escHTML(c.asignado_a||'')+'</span></div>';
        }).join('')
        +'</div>';
    }

    // Log
    if(d.log){
      html += '<details style="margin-top:18px"><summary style="cursor:pointer;color:#64748b;font-size:12px;font-weight:600">📜 Log generación</summary>'
        +'<pre style="background:#0f172a;color:#cbd5e1;padding:14px;border-radius:8px;font-size:11px;overflow:auto;max-height:280px;margin-top:8px">'+ _escHTML(d.log.join('\\n')) +'</pre></details>';
    }

    content.innerHTML = html;
  }

  async function apCargarSkus(){
    var box = document.getElementById('ap-skus-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/sku');
      var d = await r.json();
      var rows = d.configs || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Categoría</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia (d)</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob. target</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob. min</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Merma %</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote kg</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Prio</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.producto_nombre)+'</b></td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.categoria||'')+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cadencia_dias" onblur="apSkuUpdate(this)">'+(c.cadencia_dias===null?'auto':c.cadencia_dias)+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cobertura_target_dias" onblur="apSkuUpdate(this)">'+c.cobertura_target_dias+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="cobertura_min_dias" onblur="apSkuUpdate(this)">'+c.cobertura_min_dias+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="merma_pct" onblur="apSkuUpdate(this)">'+c.merma_pct+'</td>'
            +'<td style="padding:6px 10px;text-align:right;color:#64748b">'+(c.lote_size_kg||'—')+'</td>'
            +'<td style="padding:6px 10px;text-align:right" contenteditable="true" data-id="'+c.id+'" data-col="prioridad" onblur="apSkuUpdate(this)">'+c.prioridad+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>'
        +'<p style="font-size:11px;color:#64748b;margin-top:8px">💡 Click en cualquier celda para editar. Tab/blur guarda. Cadencia="auto" deja que el sistema decida por umbral.</p>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function apSkuUpdate(el){
    var id = el.dataset.id;
    var col = el.dataset.col;
    var val = el.textContent.trim();
    if(col==='cadencia_dias' && (val==='auto' || val==='' || val==='null')) val = null;
    else val = parseFloat(val);
    if(val !== null && isNaN(val)) return;
    try {
      var body = {}; body[col] = val;
      var r = await fetch('/api/auto-plan/configs/sku/'+id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      if(r.ok) el.style.background = '#dcfce7'; else el.style.background = '#fee2e2';
      setTimeout(function(){el.style.background='';}, 800);
    } catch(e){ el.style.background = '#fee2e2'; }
  }

  async function apCargarMp(){
    var box = document.getElementById('ap-mp-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/mp');
      var d = await r.json();
      var rows = d.configs || [];
      if(!rows.length){
        box.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;padding:14px;border-radius:8px;color:#92400e">⚠ No hay materiales con lead time configurado. El auto-plan usará defaults (lead 14d, buffer 30d, origen local). Para envases de China, configúralos aquí con lead 180d.</div>';
        return;
      }
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">ID</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Material</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Origen</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lead</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Buffer</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob min</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cob ideal</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Proveedor</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var origenColor = c.origen==='china'?'#dc2626':(c.origen==='local'?'#15803d':'#0891b2');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML(c.material_id)+(c.es_envase?' 📦':'')+'</td>'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.material_nombre||'')+'</b></td>'
            +'<td style="padding:6px 10px"><span style="background:'+origenColor+'22;color:'+origenColor+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.origen)+'</span></td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.lead_time_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.buffer_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.cobertura_min_dias+'d</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.cobertura_ideal_dias+'d</td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.proveedor_principal||'—')+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function apMpNuevo(){
    ['mp-id','mp-nombre','mp-prov'].forEach(function(id){document.getElementById(id).value=''});
    document.getElementById('mp-origen').value='local';
    document.getElementById('mp-envase').value='0';
    document.getElementById('mp-lead').value='14';
    document.getElementById('mp-buffer').value='30';
    document.getElementById('mp-cobmin').value='30';
    document.getElementById('mp-cobideal').value='60';
    document.getElementById('modal-mp-cfg').style.display='flex';
  }

  async function apMpGuardar(){
    var body = {
      material_id: document.getElementById('mp-id').value.trim(),
      material_nombre: document.getElementById('mp-nombre').value.trim(),
      origen: document.getElementById('mp-origen').value,
      es_envase: parseInt(document.getElementById('mp-envase').value),
      lead_time_dias: parseInt(document.getElementById('mp-lead').value),
      buffer_dias: parseInt(document.getElementById('mp-buffer').value),
      cobertura_min_dias: parseInt(document.getElementById('mp-cobmin').value),
      cobertura_ideal_dias: parseInt(document.getElementById('mp-cobideal').value),
      proveedor_principal: document.getElementById('mp-prov').value.trim(),
    };
    if(!body.material_id){ alert('ID material requerido'); return; }
    try {
      var r = await fetch('/api/auto-plan/configs/mp', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||r.status)); return; }
      document.getElementById('modal-mp-cfg').style.display='none';
      _toast('Material configurado', 1);
      apCargarMp();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apCargarEmails(){
    var box = document.getElementById('ap-emails-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/emails');
      var d = await r.json();
      var rows = d.configs || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Rol</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Nombre</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Email</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Resumen</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Alertas</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Compras</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Calidad</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Agenda</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase"></th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var ck = function(v,k){return '<input type="checkbox" '+(v?'checked':'')+' onchange="apEmailToggle(\\''+c.rol+'\\',\\''+k+'\\',this.checked)">';};
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML(c.rol)+'</td>'
            +'<td style="padding:6px 10px"><b>'+_escHTML(c.nombre||'')+'</b></td>'
            +'<td style="padding:6px 10px"><input type="email" value="'+_escAttr(c.email||'')+'" placeholder="email@dominio.com" data-rol="'+c.rol+'" onblur="apEmailUpdate(this)" style="width:100%;padding:5px 8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;background:'+(c.email?'#f0fdf4':'#fef2f2')+'"></td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_resumen_diario,'recibe_resumen_diario')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_alertas_criticas,'recibe_alertas_criticas')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_compras_aprob,'recibe_compras_aprob')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_calidad,'recibe_calidad')+'</td>'
            +'<td style="padding:6px 10px;text-align:center">'+ck(c.recibe_agenda_personal,'recibe_agenda_personal')+'</td>'
            +'<td style="padding:6px 10px;text-align:center"><button onclick="apEmailTest(\\''+_escAttr(c.email||'')+'\\')" '+(c.email?'':'disabled')+' style="background:#0891b2;color:#fff;border:none;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;'+(c.email?'':'opacity:.4')+'">📧 Test</button></td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function apEmailUpdate(input){
    try {
      var r = await fetch('/api/auto-plan/configs/emails', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({rol: input.dataset.rol, email: input.value.trim()})
      });
      if(r.ok){ input.style.background = input.value.trim() ? '#f0fdf4' : '#fef2f2'; }
    } catch(e){}
  }

  async function apEmailToggle(rol, key, val){
    var body = {rol: rol}; body[key] = val ? 1 : 0;
    try { await fetch('/api/auto-plan/configs/emails', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); } catch(e){}
  }

  async function apEmailTest(email){
    if(!email) return;
    if(!confirm('¿Enviar email de prueba a '+email+'?')) return;
    try {
      var r = await fetch('/api/auto-plan/configs/emails/test', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email: email})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'no se pudo enviar')); return; }
      _toast('📧 Test enviado a '+email+' (puede tardar 30s)', 1);
    } catch(e){ alert('Error: '+e.message); }
  }

  async function apCargarRuns(){
    var box = document.getElementById('ap-runs-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/runs');
      var d = await r.json();
      var rows = d.runs || [];
      if(!rows.length){
        box.innerHTML = '<div style="background:#f8fafc;padding:20px;border-radius:8px;text-align:center;color:#94a3b8">El auto-plan aún no se ha ejecutado. Pulsa "🔥 Ejecutar AHORA" arriba para hacer la primera corrida.</div>';
        return;
      }
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha/hora</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Por</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Tipo</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Producciones</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Compras</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Alertas</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Emails</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Tiempo</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(c){
          var tipoColor = c.tipo==='auto'?'#7c3aed':(c.tipo==='manual'?'#0891b2':'#64748b');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 10px;font-family:monospace;font-size:11px">'+_escHTML((c.ejecutado_at||'').substring(0,19))+'</td>'
            +'<td style="padding:6px 10px;font-size:11px;color:#64748b">'+_escHTML(c.ejecutado_por)+'</td>'
            +'<td style="padding:6px 10px"><span style="background:'+tipoColor+'22;color:'+tipoColor+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.tipo)+'</span></td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.producciones_creadas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+c.compras_creadas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace;color:'+(c.alertas_criticas>0?'#dc2626':'#64748b')+';font-weight:'+(c.alertas_criticas>0?'700':'400')+'">'+c.alertas_criticas+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace">'+(c.emails_enviados||0)+'</td>'
            +'<td style="padding:6px 10px;text-align:right;font-family:monospace;font-size:11px;color:#64748b">'+(c.duracion_ms||0)+'ms</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════════
  // PLAN V2 — Multi-horizonte (1sem / 1m / 2m / 3m / 6m / 1año)
  // ════════════════════════════════════════════════════════════════════════
  // Sebastian (30-abr-2026): "monte dos meses según lo que dice shopify"
  // → default 2 meses (con switcher para ver más / menos)
  var _PV2_HORIZONTE = '2';
  var _PV2_DATA = null;

  function planV2Init(){
    // Sebastian (30-abr-2026): "monte todo automáticamente desde Shopify".
    fetch('/api/auto-plan/asegurar-actualizado?max_horas=12', {method:'POST'})
      .then(function(r){return r.json();})
      .then(function(d){
        if(d.ejecutado){
          _toast('🤖 Auto-Plan recalculando en background...', 1);
          setTimeout(planV2Cargar, 35000);
        }
      }).catch(function(){});
    planV2Cargar();
    planV2DetectarCambios();
    planV2CargarStatusLine();
    planV2CargarCentroAccion();
  }

  // ════════════════════════════════════════════════════════════════════
  // STATUS LINE CONSOLIDADA — 1 línea con cobertura + calendar + margen
  // ════════════════════════════════════════════════════════════════════
  async function planV2CargarStatusLine(){
    var box = document.getElementById('pv2-status-line');
    if(!box) return;
    try {
      var [cobR, calR, audR] = await Promise.all([
        fetch('/api/planta/kpi-cobertura-skus').then(function(r){return r.json();}).catch(function(){return null;}),
        fetch('/api/planta/calendar-debug').then(function(r){return r.json();}).catch(function(){return null;}),
        fetch('/api/planta/auditoria-calendar').then(function(r){return r.json();}).catch(function(){return null;}),
      ]);
      var partes = [];
      if(cobR && cobR.cobertura_pct !== undefined){
        partes.push('🎯 ' + cobR.cobertura_pct + '% cobertura SKUs');
      }
      if(calR && calR.events !== undefined){
        partes.push('📅 ' + (calR.events.length || 0) + ' eventos Calendar');
      }
      if(audR && audR.kpis && audR.kpis.cumple_margen_pct !== undefined){
        partes.push('✓ ' + audR.kpis.cumple_margen_pct + '% margen 20d');
      }
      if(partes.length){
        box.innerHTML = partes.join(' · ');
      } else {
        box.innerHTML = 'Producciones · MP · Envases — proyectado por horizonte';
      }
    } catch(e){
      box.innerHTML = 'Producciones · MP · Envases — proyectado por horizonte';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // CENTRO DE ACCIÓN UNIFICADO — Alertas + Recomendaciones en 1 panel
  // ════════════════════════════════════════════════════════════════════
  async function planV2CargarCentroAccion(){
    var box = document.getElementById('pv2-centro-accion');
    if(!box) return;
    box.innerHTML = '<div style="background:#f1f5f9;padding:14px;border-radius:8px;font-size:13px;color:#64748b">⏳ Cargando centro de acción...</div>';
    try {
      var [alR, recR] = await Promise.all([
        fetch('/api/planta/alertas-calendar').then(function(r){return r.json();}).catch(function(){return {alertas:[],kpis:{}};}),
        fetch('/api/planta/recomendaciones').then(function(r){return r.json();}).catch(function(){return {recomendaciones:[],kpis:{}};}),
      ]);
      var alertas = (alR && alR.alertas) || [];
      var alK = (alR && alR.kpis) || {};
      var recs = (recR && recR.recomendaciones) || [];
      var recK = (recR && recR.kpis) || {};

      // Combinar alertas + recomendaciones en una sola lista de "acciones"
      // Producto único, prioridad por estado más urgente
      var accionesMap = {};
      // Alertas
      alertas.forEach(function(a){
        accionesMap[a.producto] = {
          producto: a.producto,
          tipo: 'alerta',
          estado: a.estado,
          mensaje: a.mensaje,
          proxima_fecha: a.proxima_fecha,
          dias_hasta: a.dias_hasta_proximo,
          kg: a.kg_proximo,
          velocidad_real: a.velocidad_real,
          velocidad_planeada: a.velocidad_planeada,
          ratio: a.ratio,
          diff_dias: a.diff_dias,
          urgencia_orden: ({adelantar:1, adelantar_ligero:2, reducir_lote:3, atrasar_ligero:4, sin_ventas:5, ok:6}[a.estado] || 7),
        };
      });
      // Recomendaciones (sólo si SKU no tiene alerta y es accionable)
      recs.forEach(function(r){
        if(!accionesMap[r.producto] && (r.urgencia==='critica' || r.urgencia==='alta' || r.urgencia==='media')){
          accionesMap[r.producto] = {
            producto: r.producto,
            tipo: 'recomendacion',
            estado: r.urgencia,
            mensaje: r.razon || ('Días alcance: ' + r.dias_alcance + 'd'),
            proxima_fecha: r.fecha_proxima,
            dias_hasta: null,
            kg: r.lote_tipico_kg || r.lote_kg_default,
            velocidad_real: r.velocidad_dia,
            urgencia_orden: ({critica:1, alta:2, media:3}[r.urgencia] || 8),
          };
        }
      });
      var acciones = Object.values(accionesMap);
      acciones.sort(function(a,b){return a.urgencia_orden - b.urgencia_orden;});

      if(!acciones.length){
        box.innerHTML = '<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:14px;border-radius:8px;font-size:13px;color:#065f46">✅ Sin acciones pendientes — todos los SKUs alineados con su plan</div>';
        return;
      }

      var colDeEstado = function(s){
        return s==='adelantar'||s==='critica'?'#dc2626'
          : s==='adelantar_ligero'||s==='alta'?'#f97316'
          : s==='ok'?'#10b981'
          : s==='atrasar_ligero'||s==='media'?'#eab308'
          : s==='reducir_lote'?'#a855f7'
          : '#64748b';
      };
      var labelEstado = function(s){
        return ({adelantar:'🔴 ADELANTAR',adelantar_ligero:'🟠 ADELANTAR LIGERO',ok:'🟢 OK',
                 atrasar_ligero:'🟡 ATRASAR',reducir_lote:'⚠️ REDUCIR',sin_ventas:'∅ SIN VENTAS',
                 critica:'🔴 CRÍTICA',alta:'🟠 ALTA',media:'🟡 MEDIA'}[s] || s.toUpperCase());
      };

      var criticos = acciones.filter(function(a){return a.urgencia_orden <= 2;});
      var medios = acciones.filter(function(a){return a.urgencia_orden >= 3 && a.urgencia_orden <= 5;});
      var ok = acciones.filter(function(a){return a.urgencia_orden >= 6;});

      var html = '<div style="background:#fff;border:2px solid '+(criticos.length>0?'#dc2626':'#fb923c')+';border-radius:10px;overflow:hidden">';
      html += '<div style="background:linear-gradient(135deg,'+(criticos.length>0?'#dc2626,#ea580c':'#f97316,#fbbf24')+');color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">';
      html += '<div><b style="font-size:15px">🎯 Centro de Acción</b><div style="font-size:11px;color:#fed7aa;margin-top:2px">Cruce Calendar + Velocidad real + Recomendaciones</div></div>';
      html += '<div style="display:flex;gap:6px;font-size:11px;flex-wrap:wrap">';
      if(criticos.length) html += '<span style="background:rgba(220,38,38,.4);padding:4px 10px;border-radius:6px;font-weight:800">🔴 '+criticos.length+' críticas</span>';
      if(medios.length) html += '<span style="background:rgba(234,179,8,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟡 '+medios.length+' medias</span>';
      if(ok.length) html += '<span style="background:rgba(34,197,94,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟢 '+ok.length+' OK</span>';
      html += '</div></div>';
      html += '<div style="padding:8px 12px;max-height:380px;overflow:auto">';

      function fila(a){
        var col = colDeEstado(a.estado);
        var bg = col + '12';
        return '<div style="background:'+bg+';border-left:4px solid '+col+';padding:10px 12px;margin-bottom:6px;border-radius:0 6px 6px 0">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
          +'<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(a.producto)+'</b>'
          +'<div style="font-size:11px;color:#475569;margin-top:3px">'+_escHTML(a.mensaje||'')+'</div>'
          +(a.proxima_fecha?'<div style="font-size:10px;color:#64748b;margin-top:3px">📅 Próximo: '+_escHTML(a.proxima_fecha)+(a.dias_hasta!=null?(' (en '+a.dias_hasta+'d)'):'')+(a.kg?(' · '+a.kg+' kg'):'')+'</div>':'')
          +(a.velocidad_real?'<div style="font-size:10px;color:#64748b">📊 Vel real: '+a.velocidad_real+' u/d'+(a.velocidad_planeada?(' · plan: '+a.velocidad_planeada+' u/d · ratio '+a.ratio+'×'):'')+'</div>':'')
          +'</div>'
          +'<div style="text-align:right">'
          +'<span style="background:'+col+';color:#fff;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:800;white-space:nowrap">'+labelEstado(a.estado)+'</span>'
          +(a.diff_dias?('<div style="font-size:10px;color:'+col+';margin-top:4px;font-weight:700">'+(a.diff_dias>0?'-':'+')+Math.abs(a.diff_dias)+'d</div>'):'')
          +'</div></div></div>';
      }
      criticos.forEach(function(a){html+=fila(a);});
      medios.forEach(function(a){html+=fila(a);});
      if(ok.length){
        html += '<details style="margin-top:8px"><summary style="cursor:pointer;color:#475569;font-size:12px;padding:6px;font-weight:600">🟢 '+ok.length+' SKUs en plan correcto (clic para expandir)</summary>';
        ok.forEach(function(a){html+=fila(a);});
        html += '</details>';
      }
      html += '</div></div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:12px;border-radius:8px;font-size:12px;color:#991b1b">Error cargando centro de acción: '+(e.message||'desconocido')+'</div>';
    }
  }

  async function planV2CargarAlertas(){
    var box = document.getElementById('pv2-alertas-wrap');
    if(!box) return;
    box.innerHTML = '<div style="background:#f1f5f9;padding:12px;border-radius:8px;font-size:12px;color:#64748b">⏳ Cargando alertas Calendar vs ventas...</div>';
    try {
      var r = await fetch('/api/planta/alertas-calendar');
      var d = await r.json();
      if(d.error){ box.innerHTML=''; return; }
      var alertas = d.alertas||[];
      var k = d.kpis||{};
      if(!alertas.length){
        box.innerHTML = '<div style="background:#ecfdf5;border:1px solid #6ee7b7;padding:12px;border-radius:8px;font-size:13px;color:#065f46">✅ Sin alertas — todos los SKUs están alineados con su cadencia o sin lotes próximos en 60 días</div>';
        return;
      }
      var critical = alertas.filter(function(a){return a.estado==="adelantar"||a.estado==="reducir_lote";});
      var warn = alertas.filter(function(a){return a.estado==="adelantar_ligero"||a.estado==="atrasar_ligero"||a.estado==="sin_ventas";});
      var ok = alertas.filter(function(a){return a.estado==="ok";});
      var html = '<div style="background:#fff;border:2px solid #fb923c;border-radius:10px;overflow:hidden">';
      html += '<div style="background:linear-gradient(135deg,#dc2626,#ea580c);color:#fff;padding:12px 16px;display:flex;justify-content:space-between;align-items:center">';
      html += '<div><b style="font-size:15px">🚨 Alertas Calendar vs Ventas</b><div style="font-size:11px;color:#fed7aa;margin-top:2px">Cruce de cadencia planeada con velocidad real Shopify (30d)</div></div>';
      html += '<div style="display:flex;gap:8px;font-size:11px">';
      if(k.adelantar) html += '<span style="background:rgba(220,38,38,.4);padding:4px 10px;border-radius:6px;font-weight:800">🔴 '+k.adelantar+' adelantar</span>';
      if(k.adelantar_ligero) html += '<span style="background:rgba(249,115,22,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟠 '+k.adelantar_ligero+' adelantar light</span>';
      if(k.ok) html += '<span style="background:rgba(34,197,94,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟢 '+k.ok+' OK</span>';
      if(k.atrasar_ligero) html += '<span style="background:rgba(234,179,8,.4);padding:4px 10px;border-radius:6px;font-weight:800">🟡 '+k.atrasar_ligero+' atrasar</span>';
      if(k.reducir_lote) html += '<span style="background:rgba(168,85,247,.4);padding:4px 10px;border-radius:6px;font-weight:800">⚠ '+k.reducir_lote+' reducir lote</span>';
      if(k.sin_ventas) html += '<span style="background:rgba(100,116,139,.4);padding:4px 10px;border-radius:6px;font-weight:800">∅ '+k.sin_ventas+' sin ventas</span>';
      html += '</div></div>';
      html += '<div style="padding:8px 12px;max-height:340px;overflow:auto">';

      function colDeEstado(s){
        return s==='adelantar'?'#dc2626':s==='adelantar_ligero'?'#f97316':s==='ok'?'#10b981':s==='atrasar_ligero'?'#eab308':s==='reducir_lote'?'#a855f7':'#64748b';
      }

      function fila(a){
        var col = colDeEstado(a.estado);
        var bg  = col + '12';
        return '<div style="background:'+bg+';border-left:4px solid '+col+';padding:10px 12px;margin-bottom:6px;border-radius:0 6px 6px 0">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">'
          +'<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(a.producto)+'</b>'
          +'<div style="font-size:11px;color:#475569;margin-top:3px">'+_escHTML(a.mensaje)+'</div>'
          +'<div style="font-size:10px;color:#64748b;margin-top:3px">📅 Próximo lote: '+_escHTML(a.proxima_fecha)+' (en '+a.dias_hasta_proximo+'d) · '+a.kg_proximo+' kg · '+(a.unidades_lote||0)+' u</div>'
          +'<div style="font-size:10px;color:#64748b">📊 Velocidad real: '+(a.velocidad_real||0)+' u/d · planeada: '+(a.velocidad_planeada||0)+' u/d · ratio: '+(a.ratio||0)+'×</div>'
          +'</div>'
          +'<div style="text-align:right"><span style="background:'+col+';color:#fff;padding:4px 10px;border-radius:6px;font-size:10px;font-weight:800;text-transform:uppercase">'+a.estado.replace(/_/g," ")+'</span>'
          +(a.diff_dias?('<div style="font-size:10px;color:'+col+';margin-top:4px;font-weight:700">'+(a.diff_dias>0?'-':'+')+Math.abs(a.diff_dias)+'d</div>'):'')
          +'</div></div></div>';
      }

      // Críticos primero
      critical.forEach(function(a){ html += fila(a); });
      warn.forEach(function(a){ html += fila(a); });
      // OK colapsado
      if(ok.length){
        html += '<details style="margin-top:8px"><summary style="cursor:pointer;color:#475569;font-size:12px;padding:6px">🟢 '+ok.length+' SKUs en plan correcto (clic para expandir)</summary>';
        ok.forEach(function(a){ html += fila(a); });
        html += '</details>';
      }
      html += '</div></div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:10px;border-radius:8px;font-size:12px;color:#991b1b">Error cargando alertas: '+(e.message||'desconocido')+'</div>';
    }
  }

  async function planV2CargarAuditoria(){
    var box = document.getElementById('pv2-auditoria');
    if(!box) return;
    try {
      var r = await fetch('/api/planta/auditoria-calendar');
      var d = await r.json();
      var k = d.kpis || {};
      if((d.total||0) === 0){
        box.style.display = 'none';
        return;
      }
      box.style.display = 'block';
      var pct = k.cumple_margen_pct || 0;
      var col = pct >= 80 ? '#86efac' : (pct >= 60 ? '#fcd34d' : '#fca5a5');
      var icon = pct >= 80 ? '✓' : (pct >= 60 ? '⚠' : '🔴');
      box.innerHTML = '<b style="color:'+col+'">'+icon+' '+pct+'% cumple margen 20d</b> '
        + '· de '+d.total+' producciones en Calendar: '
        + (k.ok ? '<b style="color:#86efac">'+k.ok+' OK</b> · ' : '')
        + (k.temprana ? '<span style="color:#93c5fd">'+k.temprana+' tempranas</span> · ' : '')
        + (k.ajustada ? '<span style="color:#fcd34d">'+k.ajustada+' ajustadas</span> · ' : '')
        + (k.tarde ? '<span style="color:#fb923c">'+k.tarde+' tardes</span> · ' : '')
        + (k.stockout ? '<b style="color:#fca5a5">'+k.stockout+' stock-outs</b>' : '')
        + ' <a href="#" onclick="planV2VerAuditoria();return false" style="color:#fff;text-decoration:underline;margin-left:6px">ver detalle</a>';
    } catch(e){ /* silent */ }
  }

  async function planV2VerAuditoria(){
    try {
      var r = await fetch('/api/planta/auditoria-calendar');
      var d = await r.json();
      var auditorias = d.auditorias || [];
      var modal = document.createElement('div');
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
      modal.onclick = function(e){if(e.target===modal)modal.remove();};
      var byClase = {ok:'#15803d',temprana:'#0891b2',ajustada:'#d97706',tarde:'#dc2626',stockout:'#7f1d1d'};
      var html = '<div style="background:#fff;border-radius:12px;width:900px;max-width:96vw;max-height:90vh;overflow:auto;padding:20px">'
        +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px"><h3 style="margin:0;color:#0f172a">📊 Auditoría Calendar · margen 20d</h3><button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>'
        +'<p style="color:#64748b;font-size:12px;margin:0 0 14px">Para cada producción del Calendar, calculamos cuánto cubría el lote anterior vs cuándo se hizo la siguiente. Si el margen real ≥ 20 días → se cumplió la regla.</p>';
      if(!auditorias.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">Sin pares consecutivos para auditar</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
          +'<thead style="background:#f9fafb"><tr>'
          +'<th style="padding:8px;text-align:left">Producto</th>'
          +'<th style="padding:8px;text-align:left">Anterior</th>'
          +'<th style="padding:8px;text-align:left">Actual</th>'
          +'<th style="padding:8px;text-align:right">Gap</th>'
          +'<th style="padding:8px;text-align:right">Cubre</th>'
          +'<th style="padding:8px;text-align:right">Margen</th>'
          +'<th style="padding:8px;text-align:left">Estado</th>'
          +'</tr></thead><tbody>';
        auditorias.forEach(function(a){
          var col = byClase[a.clase] || '#64748b';
          html += '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:6px 8px"><b>'+_escHTML(a.producto)+'</b></td>'
            +'<td style="padding:6px 8px;font-size:11px">'+_escHTML(a.fecha_anterior)+'<br><span style="color:#64748b">'+a.kg_anterior+'kg</span></td>'
            +'<td style="padding:6px 8px;font-size:11px">'+_escHTML(a.fecha_actual)+'</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+a.gap_dias+'d</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+a.duracion_estimada_lote+'d</td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:'+col+'">'+(a.margen_dias>0?'+':'')+a.margen_dias+'d</td>'
            +'<td style="padding:6px 8px"><span style="background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase">'+a.clase+'</span></td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';
      modal.innerHTML = html;
      document.body.appendChild(modal);
    } catch(e){ alert('Error: '+e.message); }
  }

  // ════════════════════════════════════════════════════════════════════
  // 🔍 DIAGNÓSTICO SKU — lo que el sistema LEE crudo de Shopify
  // ════════════════════════════════════════════════════════════════════
  async function planV2DiagnosticoSKU(){
    // Paso 1: cargar lista de productos
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;text-align:center"><div style="font-size:32px">⏳</div><div style="margin-top:10px;color:#64748b">Cargando productos...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/diagnostico-sku?listar=1');
      var d = await r.json();
      var prods = d.productos || [];
      var html = '<div style="background:#fff;border-radius:12px;width:600px;max-width:96vw;max-height:90vh;overflow:auto;padding:24px">';
      html += '<h3 style="margin:0 0 14px;color:#0f172a">🔍 Selecciona un producto a diagnosticar</h3>';
      html += '<p style="color:#64748b;font-size:12px;margin:0 0 14px">Vamos a ver crudo lo que el sistema lee de Shopify para ese producto: SKUs mapeados, stock, ventas, velocidad, días de alcance.</p>';
      html += '<input type="text" id="diagSkuFiltro" oninput="planV2DiagFiltrar()" placeholder="Filtrar..." style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;margin-bottom:10px">';
      html += '<div id="diagSkuLista" style="max-height:50vh;overflow:auto">';
      prods.forEach(function(p){
        var col = p.estado === 'activo' ? '#0f172a' : '#94a3b8';
        html += '<div class="diag-item" data-nombre="'+_escHTML((p.nombre||'').toLowerCase())+'" onclick="planV2DiagnosticoVer(\\''+_escHTML((p.nombre||'').replace(/\\x27/g,"\\\\\\x27"))+'\\')" style="padding:10px;border-bottom:1px solid #f1f5f9;cursor:pointer;display:flex;justify-content:space-between;color:'+col+'" onmouseover="this.style.background=\\'#f8fafc\\'" onmouseout="this.style.background=\\'#fff\\'">';
        html += '<span><b>'+_escHTML(p.nombre)+'</b></span><span style="color:#64748b;font-size:11px">P'+(p.prioridad||'-')+' · '+_escHTML(p.estado||'')+'</span>';
        html += '</div>';
      });
      html += '</div></div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  function planV2DiagFiltrar(){
    var q = (document.getElementById('diagSkuFiltro').value||'').toLowerCase();
    var items = document.querySelectorAll('.diag-item');
    items.forEach(function(it){
      var n = it.getAttribute('data-nombre') || '';
      it.style.display = (!q || n.indexOf(q) >= 0) ? '' : 'none';
    });
  }

  async function planV2DiagnosticoVer(producto){
    // Cierra modal anterior
    document.querySelectorAll('div[style*="position:fixed"][style*="z-index:9999"]').forEach(function(m){m.remove();});
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:50px;text-align:center"><div style="font-size:42px">🔍</div><div style="margin-top:14px;color:#0f172a;font-size:16px;font-weight:700">Analizando "'+_escHTML(producto)+'"...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/diagnostico-sku?producto='+encodeURIComponent(producto));
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }

      var html = '<div style="background:#fff;border-radius:12px;width:1100px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:14px">';
      html += '<div><h2 style="margin:0;color:#0f172a;font-size:22px">🔍 Diagnóstico: '+_escHTML(d.producto)+'</h2>';
      html += '<p style="color:#64748b;font-size:11px;margin:4px 0 0">Análisis: '+_escHTML(d.timestamp_actual||'')+'</p></div>';
      html += '<button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 14px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>';

      // Advertencias
      if((d.advertencias||[]).length){
        html += '<div style="background:#fef2f2;border:1px solid #fca5a5;padding:12px;border-radius:8px;margin-bottom:16px">';
        d.advertencias.forEach(function(a){
          html += '<div style="color:#991b1b;font-size:12px;margin-bottom:4px">'+_escHTML(a)+'</div>';
        });
        html += '</div>';
      }

      // 1. SKUs mapeados
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">1️⃣ SKUs Shopify mapeados a este producto</h4>';
      var skus = d.skus_mapeados||[];
      if(!skus.length){
        html += '<div style="color:#dc2626;font-size:12px">⚠ NINGÚN SKU mapeado. Sin esto el sistema no puede leer Shopify.</div>';
      } else {
        html += '<div style="display:flex;gap:8px;flex-wrap:wrap">';
        skus.forEach(function(s){
          html += '<span style="background:'+(s.activo?'#dbeafe':'#f1f5f9')+';color:'+(s.activo?'#1e3a8a':'#64748b')+';padding:6px 12px;border-radius:6px;font-family:monospace;font-weight:700">'+_escHTML(s.sku)+(s.activo?'':' (inactivo)')+'</span>';
        });
        html += '</div>';
      }
      html += '</div>';

      // 2. Stock por SKU
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">2️⃣ Stock actual por SKU (tabla stock_pt)</h4>';
      html += '<div style="font-size:24px;font-weight:800;color:#0f172a;margin-bottom:10px">'+_fmtMiles(d.stock_total_unidades||0)+' <span style="font-size:13px;font-weight:500;color:#64748b">unidades total</span></div>';
      var stockSku = d.stock_por_sku||[];
      stockSku.forEach(function(s){
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px">';
        html += '<div style="display:flex;justify-content:space-between;font-weight:700;color:#0f172a"><span>'+_escHTML(s.sku)+'</span><span>'+(s.total_unidades||0)+' u · '+(s.lotes_count||0)+' lote(s)</span></div>';
        if((s.lotes||[]).length){
          html += '<table style="width:100%;font-size:11px;margin-top:6px;border-collapse:collapse"><thead style="color:#64748b"><tr><th style="text-align:left;padding:3px">Lote</th><th style="text-align:left">Fecha</th><th style="text-align:right">Inicial</th><th style="text-align:right">Disponible</th><th>Estado</th></tr></thead><tbody>';
          s.lotes.forEach(function(l){
            var col = l.estado === 'AGOTADO' ? '#94a3b8' : '#0f172a';
            html += '<tr style="color:'+col+'"><td style="padding:3px">'+_escHTML(l.lote||'')+'</td><td>'+_escHTML(l.fecha||'')+'</td><td style="text-align:right">'+l.inicial+'</td><td style="text-align:right;font-weight:700">'+l.disponible+'</td><td>'+_escHTML(l.estado)+'</td></tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      });
      html += '</div>';

      // 3. Ventas por periodo
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">3️⃣ Ventas Shopify por periodo</h4>';
      var vp = d.ventas_por_periodo||{};
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">';
      ['30d','60d','90d','365d'].forEach(function(p){
        var pp = vp[p]||{};
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:10px"><div style="font-size:11px;color:#64748b">Últimos '+p+'</div><div style="font-size:22px;font-weight:800;color:#0f172a">'+_fmtMiles(pp.total_unidades||0)+'</div><div style="font-size:11px;color:#64748b">'+(pp.velocidad_promedio||0)+' u/día prom.</div></div>';
      });
      html += '</div></div>';

      // 4. Velocidad final usada por motor
      var vf = d.velocidad_final||{};
      html += '<div style="background:#ecfdf5;border:2px solid #10b981;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#065f46">4️⃣ Velocidad que USA el motor (con tendencia)</h4>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px">';
      html += '<div><div style="font-size:11px;color:#065f46">Base 30d</div><div style="font-size:18px;font-weight:800">'+(vf.velocidad_base||0)+' u/d</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Factor tendencia</div><div style="font-size:18px;font-weight:800">×'+(vf.factor_tendencia||1)+'</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Velocidad ajustada</div><div style="font-size:22px;font-weight:800;color:#047857">'+(vf.unidades_por_dia||0)+' u/d</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Por semana</div><div style="font-size:18px;font-weight:800">'+(vf.unidades_por_semana||0)+' u</div></div>';
      html += '<div><div style="font-size:11px;color:#065f46">Por mes</div><div style="font-size:18px;font-weight:800">'+(vf.unidades_por_mes||0)+' u</div></div>';
      html += '</div></div>';

      // 5. Días de alcance + recomendación
      var alc = d.dias_alcance_hoy;
      var col = alc==null ? '#94a3b8' : (alc<20 ? '#dc2626' : (alc<40 ? '#f97316' : '#10b981'));
      html += '<div style="background:'+col+'15;border:2px solid '+col+';border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:'+col+'">5️⃣ Días de alcance HOY</h4>';
      html += '<div style="font-size:42px;font-weight:800;color:'+col+'">'+(alc==null?'—':alc+' días')+'</div>';
      if(d.fecha_stockout_proyectada){
        html += '<div style="font-size:13px;color:#0f172a">Stockout proyectado: <b>'+_escHTML(d.fecha_stockout_proyectada)+'</b></div>';
      }
      if(d.fecha_lote_recomendada){
        html += '<div style="font-size:13px;color:#0f172a;margin-top:4px">Lote recomendado: <b>'+_escHTML(d.fecha_lote_recomendada)+'</b></div>';
      }
      html += '<div style="font-size:13px;color:'+col+';margin-top:6px;font-weight:700">'+_escHTML(d.urgencia||'')+'</div>';
      html += '</div>';

      // 6. Lote típico + factor g/u
      var l = d.lote||{};
      html += '<div style="background:#f8fafc;border-radius:8px;padding:14px;margin-bottom:14px">';
      html += '<h4 style="margin:0 0 10px;color:#0f172a">6️⃣ Lote y factor g/u</h4>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px">';
      html += '<div><div style="font-size:11px;color:#64748b">Factor g/u (motor)</div><div style="font-size:20px;font-weight:800">'+(d.factor_g_por_unidad||0)+' g</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote default fórmula</div><div style="font-size:20px;font-weight:800">'+(l.lote_default_formula||0)+' kg</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote típico (mediana)</div><div style="font-size:20px;font-weight:800">'+(l.lote_tipico_historico||0)+' kg</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Unidades por lote</div><div style="font-size:20px;font-weight:800;color:#0891b2">'+_fmtMiles(d.unidades_por_lote||0)+' u</div></div>';
      html += '<div><div style="font-size:11px;color:#64748b">Lote durará</div><div style="font-size:20px;font-weight:800">'+(d.dias_que_durara_lote==null?'—':d.dias_que_durara_lote+' d')+'</div></div>';
      html += '</div>';
      if((l.historico_kg_lista||[]).length){
        html += '<div style="margin-top:8px;font-size:11px;color:#64748b">Histórico Calendar (kg): '+l.historico_kg_lista.join(', ')+'</div>';
      }
      html += '</div>';

      // 7. Cálculo paso a paso
      html += '<div style="background:#1e293b;color:#e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;font-family:monospace;font-size:12px">';
      html += '<h4 style="margin:0 0 10px;color:#f8fafc;font-family:system-ui">7️⃣ Cálculo paso a paso</h4>';
      (d.ejemplo_calculo||[]).forEach(function(line){
        html += '<div style="margin-bottom:4px">'+_escHTML(line)+'</div>';
      });
      html += '</div>';

      // 8. Últimos pedidos con este producto
      var ult = d.ultimos_10_pedidos_con_este_producto||[];
      if(ult.length || ult.error){
        html += '<div style="background:#f8fafc;border-radius:8px;padding:14px">';
        html += '<h4 style="margin:0 0 10px;color:#0f172a">8️⃣ Últimos pedidos Shopify con este producto</h4>';
        if(ult.error){
          html += '<div style="color:#dc2626;font-size:12px">Error: '+_escHTML(ult.error)+'</div>';
        } else if(!ult.length){
          html += '<div style="color:#64748b;font-size:12px">Sin pedidos recientes encontrados.</div>';
        } else {
          html += '<table style="width:100%;font-size:12px;border-collapse:collapse"><thead style="background:#f1f5f9"><tr><th style="padding:6px;text-align:left">Fecha</th><th style="padding:6px;text-align:left">Pedido</th><th style="padding:6px;text-align:left">SKU</th><th style="padding:6px;text-align:right">Cantidad</th></tr></thead><tbody>';
          ult.forEach(function(u){
            html += '<tr style="border-top:1px solid #e2e8f0"><td style="padding:5px 6px">'+_escHTML(u.fecha||'')+'</td><td style="padding:5px 6px">'+_escHTML(u.pedido||'')+'</td><td style="padding:5px 6px;font-family:monospace">'+_escHTML(u.sku||'')+'</td><td style="padding:5px 6px;text-align:right;font-weight:700">'+(u.cantidad||0)+'</td></tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      }

      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 🛒 Plan SOLO Shopify — vista por día (próximo lunes → viernes)
  // ════════════════════════════════════════════════════════════════════
  async function planV2VerSemanaShopify(){
    // Pregunta cuántas semanas
    var semanasStr = prompt('¿Cuántas semanas planear?\\n(1 = solo próxima semana, 2 = dos semanas, 4 = mes completo)', '1');
    if(semanasStr === null) return;
    var semanas = Math.max(1, Math.min(8, parseInt(semanasStr) || 1));
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:40px;text-align:center"><div style="font-size:32px">⏳</div><div style="margin-top:10px;color:#64748b">Calculando plan SOLO con Shopify...</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/plan-semana-shopify?semanas='+semanas);
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      var k = d.kpis || {};
      var dias = d.dias || [];
      var sin = d.sin_slot || [];
      var urgCol = {critica:'#dc2626',alta:'#f97316',media:'#eab308',baja:'#3b82f6'};
      var urgEmoji = {critica:'🔴',alta:'🟠',media:'🟡',baja:'🔵'};
      var html = '<div style="background:#fff;border-radius:12px;width:1100px;max-width:96vw;max-height:90vh;overflow:auto;padding:24px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px">';
      html += '<div><h2 style="margin:0;color:#0f172a;font-size:22px">🛒 Plan de la semana — SOLO Shopify</h2>';
      html += '<p style="color:#64748b;font-size:12px;margin:6px 0 0">Sin tener en cuenta el Calendar. Stock = Shopify · Velocidad = ventas 30d · Margen = 20d</p>';
      html += '<p style="color:#0f172a;font-size:13px;margin:8px 0 0"><b>Semana del '+_escHTML(d.semana_inicio)+' al '+_escHTML(d.semana_fin)+'</b> · '+_escHTML(d.patron_distribucion)+' · '+(d.semanas||1)+' semana(s)</p></div>';
      html += '<button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="background:#fff;border:1px solid #cbd5e1;padding:6px 12px;border-radius:6px;cursor:pointer">Cerrar ✕</button></div>';
      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:18px">';
      html += '<div style="background:#f1f5f9;padding:10px;border-radius:8px"><div style="font-size:11px;color:#64748b">Asignadas</div><div style="font-size:22px;font-weight:800;color:#0f172a">'+(k.asignadas_semana||0)+'</div></div>';
      html += '<div style="background:#fee2e2;padding:10px;border-radius:8px"><div style="font-size:11px;color:#991b1b">🔴 Críticas</div><div style="font-size:22px;font-weight:800;color:#dc2626">'+(k.criticas||0)+'</div></div>';
      html += '<div style="background:#fed7aa;padding:10px;border-radius:8px"><div style="font-size:11px;color:#9a3412">🟠 Altas</div><div style="font-size:22px;font-weight:800;color:#f97316">'+(k.altas||0)+'</div></div>';
      html += '<div style="background:#fef3c7;padding:10px;border-radius:8px"><div style="font-size:11px;color:#854d0e">🟡 Medias</div><div style="font-size:22px;font-weight:800;color:#eab308">'+(k.medias||0)+'</div></div>';
      html += '<div style="background:#e0e7ff;padding:10px;border-radius:8px"><div style="font-size:11px;color:#3730a3">🔵 Bajas</div><div style="font-size:22px;font-weight:800;color:#3b82f6">'+(k.bajas||0)+'</div></div>';
      if(k.sin_cupo){
        html += '<div style="background:#fce7f3;padding:10px;border-radius:8px"><div style="font-size:11px;color:#9d174d">⚠ Sin cupo</div><div style="font-size:22px;font-weight:800;color:#be185d">'+k.sin_cupo+'</div></div>';
      }
      html += '</div>';
      // Reglas usadas
      html += '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:12px;color:#78350f">';
      html += '<b>📐 Reglas aplicadas:</b><ul style="margin:6px 0 0 18px;padding:0">';
      (d.reglas||[]).forEach(function(r){ html += '<li>'+_escHTML(r)+'</li>'; });
      html += '</ul></div>';
      // Tabla por día
      if(!dias.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8;background:#f8fafc;border-radius:8px">No hay días de producción en el rango</div>';
      } else {
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:16px">';
        dias.forEach(function(dia){
          var bgHeader = dia.producciones_count > 0 ? 'linear-gradient(135deg,#0f766e,#0891b2)' : '#94a3b8';
          html += '<div style="background:#fff;border:2px solid '+(dia.producciones_count>0?'#0f766e':'#e2e8f0')+';border-radius:10px;overflow:hidden">';
          html += '<div style="background:'+bgHeader+';color:#fff;padding:10px 14px"><div style="font-size:11px;opacity:.85;text-transform:uppercase">'+_escHTML(dia.nombre_dia)+'</div><div style="font-size:16px;font-weight:800">'+_escHTML(dia.fecha)+'</div><div style="font-size:11px;margin-top:2px">'+dia.producciones_count+' producci'+(dia.producciones_count===1?'ón':'ones')+'</div></div>';
          if(dia.producciones_count === 0){
            html += '<div style="padding:18px;text-align:center;color:#94a3b8;font-size:12px;font-style:italic">— día libre —</div>';
          } else {
            html += '<div style="padding:8px">';
            dia.producciones.forEach(function(p){
              var col = urgCol[p.urgencia] || '#64748b';
              var emo = urgEmoji[p.urgencia] || '⚪';
              html += '<div style="border-left:4px solid '+col+';background:#f8fafc;padding:8px 10px;margin-bottom:6px;border-radius:0 6px 6px 0">';
              html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px">';
              html += '<div style="flex:1"><b style="color:#0f172a;font-size:13px">'+_escHTML(p.producto)+'</b>';
              html += '<div style="font-size:11px;color:#64748b;margin-top:2px">'+p.lote_kg+' kg → '+p.unidades_lote+' u · durará ~'+p.dias_que_durara_lote+'d</div></div>';
              html += '<span style="background:'+col+'22;color:'+col+';padding:2px 6px;border-radius:4px;font-size:10px;font-weight:800">'+emo+' '+p.urgencia.toUpperCase()+'</span>';
              html += '</div>';
              html += '<div style="font-size:10px;color:#475569;margin-top:4px">📦 Stock '+p.stock_actual+'u · 📈 '+p.velocidad_dia+' u/día · ⏰ alcance '+p.dias_alcance+'d</div>';
              html += '<div style="font-size:11px;color:#334155;margin-top:4px;font-style:italic">"'+_escHTML(p.razon)+'"</div>';
              html += '</div>';
            });
            html += '</div>';
          }
          html += '</div>';
        });
        html += '</div>';
      }
      // Sin cupo (overflow)
      if(sin.length){
        html += '<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:14px;margin-top:14px"><b style="color:#991b1b">⚠ Sin cupo en la(s) semana(s) — '+sin.length+' SKUs</b>';
        html += '<p style="font-size:12px;color:#7f1d1d;margin:6px 0">Estos productos tienen necesidad pero no caben con 1/día. Considera planear más semanas o desbloquear más slots.</p>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:8px"><thead style="background:#fee2e2"><tr><th style="padding:6px;text-align:left">Producto</th><th style="padding:6px;text-align:right">Lote</th><th style="padding:6px;text-align:right">Días alcance</th><th style="padding:6px;text-align:left">Urgencia</th></tr></thead><tbody>';
        sin.forEach(function(s){
          var col = urgCol[s.urgencia] || '#64748b';
          html += '<tr style="border-top:1px solid #fee2e2"><td style="padding:5px 6px"><b>'+_escHTML(s.producto)+'</b></td><td style="padding:5px 6px;text-align:right">'+s.lote_kg+' kg</td><td style="padding:5px 6px;text-align:right">'+s.dias_alcance+'d</td><td style="padding:5px 6px"><span style="color:'+col+';font-weight:700">'+s.urgencia.toUpperCase()+'</span></td></tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // 📆 Plan LARGO — 6 meses / 1 año Shopify rolling forecast
  // ════════════════════════════════════════════════════════════════════
  // Cache para CSV download
  window._planLargoData = null;
  async function planV2VerLargoShopify(meses){
    var modal = document.createElement('div');
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:9999;display:flex;align-items:center;justify-content:center;padding:20px';
    modal.onclick = function(e){if(e.target===modal)modal.remove();};
    modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:50px;text-align:center"><div style="font-size:42px">⏳</div><div style="margin-top:14px;color:#0f172a;font-size:16px;font-weight:700">Calculando plan de '+meses+' meses...</div><div style="margin-top:6px;color:#64748b;font-size:12px">Simulando rolling forecast día-a-día</div></div>';
    document.body.appendChild(modal);
    try {
      var r = await fetch('/api/planta/plan-largo-shopify?meses='+meses);
      var d = await r.json();
      if(d.error){ modal.remove(); alert('Error: '+d.error); return; }
      window._planLargoData = d;
      var k = d.kpis || {};
      var porMes = d.producciones_por_mes || {};
      var porSku = d.producciones_por_sku || {};
      var sinVentas = d.sin_ventas || [];
      var producciones = d.producciones || [];
      var titulo = meses === 12 ? '🗓️ Plan 1 año' : '📆 Plan '+meses+' meses';
      var bgGrad = meses === 12 ? 'linear-gradient(135deg,#06b6d4,#0891b2)' : 'linear-gradient(135deg,#10b981,#059669)';

      var html = '<div style="background:#fff;border-radius:12px;width:1300px;max-width:96vw;max-height:92vh;overflow:auto;padding:24px">';
      // Header
      html += '<div style="background:'+bgGrad+';color:#fff;border-radius:10px;padding:16px 20px;margin-bottom:18px">';
      html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px">';
      html += '<div><h2 style="margin:0;color:#fff;font-size:24px">'+titulo+' — SOLO Shopify</h2>';
      html += '<p style="color:#cffafe;font-size:12px;margin:4px 0 0">Rolling forecast día-a-día · '+_escHTML(d.fecha_inicio)+' → '+_escHTML(d.fecha_fin)+'</p></div>';
      html += '<div style="display:flex;gap:6px"><button onclick="planLargoCSV()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px">📥 CSV</button>';
      html += '<button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="background:rgba(255,255,255,.25);border:1px solid rgba(255,255,255,.4);color:#fff;padding:8px 14px;border-radius:6px;cursor:pointer;font-weight:700;font-size:12px">Cerrar ✕</button></div>';
      html += '</div></div>';

      // KPIs
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:18px">';
      html += '<div style="background:#ecfdf5;padding:12px;border-radius:8px;border:1px solid #6ee7b7"><div style="font-size:11px;color:#065f46">Total lotes</div><div style="font-size:26px;font-weight:800;color:#047857">'+(k.total_lotes||0)+'</div></div>';
      html += '<div style="background:#eff6ff;padding:12px;border-radius:8px;border:1px solid #93c5fd"><div style="font-size:11px;color:#1e3a8a">Total kg</div><div style="font-size:26px;font-weight:800;color:#1d4ed8">'+_fmtMiles(k.total_kg||0)+'</div></div>';
      html += '<div style="background:#fdf4ff;padding:12px;border-radius:8px;border:1px solid #d8b4fe"><div style="font-size:11px;color:#581c87">SKUs planeados</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.productos_planeados||0)+'</div></div>';
      html += '<div style="background:#fff7ed;padding:12px;border-radius:8px;border:1px solid #fdba74"><div style="font-size:11px;color:#7c2d12">Lotes/mes</div><div style="font-size:26px;font-weight:800;color:#ea580c">'+(k.promedio_lotes_por_mes||0)+'</div></div>';
      html += '<div style="background:#f1f5f9;padding:12px;border-radius:8px"><div style="font-size:11px;color:#475569">Días con producción</div><div style="font-size:26px;font-weight:800;color:#1e293b">'+(k.dias_con_produccion||0)+'</div></div>';
      if(k.alerta_capacidad){
        html += '<div style="background:#fee2e2;padding:12px;border-radius:8px;border:1px solid #fca5a5"><div style="font-size:11px;color:#991b1b">⚠ Forzados (cap.)</div><div style="font-size:26px;font-weight:800;color:#dc2626">'+(k.forzados_por_capacidad||0)+'</div></div>';
      }
      if(k.productos_sin_ventas){
        html += '<div style="background:#fef3c7;padding:12px;border-radius:8px;border:1px solid #fcd34d"><div style="font-size:11px;color:#92400e">Sin ventas</div><div style="font-size:26px;font-weight:800;color:#d97706">'+k.productos_sin_ventas+'</div></div>';
      }
      html += '</div>';

      // Reglas
      html += '<div style="background:#f0fdfa;border:1px solid #5eead4;border-radius:8px;padding:10px 14px;margin-bottom:18px;font-size:12px;color:#134e4a">';
      html += '<b>📐 Reglas aplicadas:</b><ul style="margin:6px 0 0 18px;padding:0">';
      (d.reglas||[]).forEach(function(r){ html += '<li>'+_escHTML(r)+'</li>'; });
      html += '</ul></div>';

      // Tabs internas
      html += '<div style="display:flex;gap:6px;margin-bottom:14px;border-bottom:2px solid #e2e8f0">';
      html += '<button class="plLargo-tab" data-tab="mes" onclick="planLargoTab(\\'mes\\')" style="padding:8px 16px;border:none;background:#0891b2;color:#fff;font-weight:800;cursor:pointer;border-radius:6px 6px 0 0">📅 Por mes</button>';
      html += '<button class="plLargo-tab" data-tab="sku" onclick="planLargoTab(\\'sku\\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">📦 Por SKU</button>';
      html += '<button class="plLargo-tab" data-tab="lista" onclick="planLargoTab(\\'lista\\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">📋 Lista cronológica</button>';
      if(sinVentas.length){
        html += '<button class="plLargo-tab" data-tab="sin" onclick="planLargoTab(\\'sin\\')" style="padding:8px 16px;border:none;background:#f1f5f9;color:#475569;font-weight:700;cursor:pointer;border-radius:6px 6px 0 0">⚠ Sin ventas ('+sinVentas.length+')</button>';
      }
      html += '</div>';

      // Vista por mes (default)
      html += '<div id="plLargo-vista-mes">';
      var meses_keys = Object.keys(porMes).sort();
      if(!meses_keys.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8;background:#f8fafc;border-radius:8px">No hay producciones planeadas</div>';
      } else {
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px">';
        meses_keys.forEach(function(mk){
          var lotes = porMes[mk] || [];
          var totalKg = lotes.reduce(function(s,l){return s+(l.lote_kg||0);},0);
          html += '<div style="background:#fff;border:2px solid #0891b2;border-radius:10px;overflow:hidden">';
          html += '<div style="background:linear-gradient(135deg,#0891b2,#0e7490);color:#fff;padding:10px 14px"><div style="font-size:11px;opacity:.85;text-transform:uppercase">Mes</div><div style="font-size:18px;font-weight:800">'+_escHTML(mk)+'</div><div style="font-size:11px;margin-top:2px">'+lotes.length+' lotes · '+_fmtMiles(Math.round(totalKg))+' kg</div></div>';
          html += '<div style="padding:8px;max-height:300px;overflow:auto">';
          lotes.forEach(function(l){
            html += '<div style="background:#f8fafc;padding:6px 10px;margin-bottom:4px;border-radius:6px;border-left:3px solid #0891b2;font-size:11px">';
            html += '<b style="color:#0f172a">'+_escHTML(l.producto)+'</b>';
            html += '<div style="color:#64748b">'+_escHTML(l.fecha)+' ('+_escHTML(l.dia_semana)+') · '+l.lote_kg+' kg</div>';
            html += '</div>';
          });
          html += '</div></div>';
        });
        html += '</div>';
      }
      html += '</div>';

      // Vista por SKU (oculta inicialmente)
      html += '<div id="plLargo-vista-sku" style="display:none">';
      var skus_sorted = Object.keys(porSku).sort(function(a,b){return porSku[b].total_lotes - porSku[a].total_lotes;});
      if(!skus_sorted.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">No hay SKUs planeados</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f1f5f9"><tr>';
        html += '<th style="padding:10px;text-align:left">Producto</th>';
        html += '<th style="padding:10px;text-align:right">Velocidad</th>';
        html += '<th style="padding:10px;text-align:right">Lotes</th>';
        html += '<th style="padding:10px;text-align:right">Total kg</th>';
        html += '<th style="padding:10px;text-align:left">Fechas programadas</th>';
        html += '</tr></thead><tbody>';
        skus_sorted.forEach(function(sku){
          var info = porSku[sku];
          html += '<tr style="border-top:1px solid #e2e8f0">';
          html += '<td style="padding:8px 10px"><b>'+_escHTML(sku)+'</b></td>';
          html += '<td style="padding:8px 10px;text-align:right;font-family:monospace">'+(info.velocidad_dia||0)+' u/d</td>';
          html += '<td style="padding:8px 10px;text-align:right;font-weight:700">'+info.total_lotes+'</td>';
          html += '<td style="padding:8px 10px;text-align:right;font-family:monospace">'+_fmtMiles(Math.round(info.total_kg))+' kg</td>';
          html += '<td style="padding:8px 10px;font-size:11px;color:#64748b">'+(info.fechas||[]).slice(0,8).join(' · ')+(info.fechas.length>8?' +'+(info.fechas.length-8)+' más':'')+'</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';

      // Vista lista cronológica
      html += '<div id="plLargo-vista-lista" style="display:none">';
      if(!producciones.length){
        html += '<div style="text-align:center;padding:40px;color:#94a3b8">No hay producciones</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
        html += '<thead style="background:#f1f5f9"><tr>';
        html += '<th style="padding:8px;text-align:left">Fecha</th>';
        html += '<th style="padding:8px;text-align:left">Día</th>';
        html += '<th style="padding:8px;text-align:left">Producto</th>';
        html += '<th style="padding:8px;text-align:right">Lote</th>';
        html += '<th style="padding:8px;text-align:right">Stock antes</th>';
        html += '<th style="padding:8px;text-align:right">Stock después</th>';
        html += '<th style="padding:8px;text-align:left">Motivo</th>';
        html += '</tr></thead><tbody>';
        producciones.forEach(function(p){
          var col = p.forzado_capacidad ? '#dc2626' : '#0f172a';
          html += '<tr style="border-top:1px solid #f1f5f9">';
          html += '<td style="padding:6px 8px;font-family:monospace;color:'+col+'">'+_escHTML(p.fecha)+'</td>';
          html += '<td style="padding:6px 8px;font-size:11px">'+_escHTML(p.dia_semana)+'</td>';
          html += '<td style="padding:6px 8px"><b>'+_escHTML(p.producto)+'</b>'+(p.forzado_capacidad?' <span style="background:#fee2e2;color:#dc2626;padding:1px 5px;border-radius:3px;font-size:9px">⚠ FORZADO</span>':'')+'</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace">'+p.lote_kg+' kg</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace;color:#64748b">'+p.stock_antes+'</td>';
          html += '<td style="padding:6px 8px;text-align:right;font-family:monospace;color:#15803d">'+p.stock_despues+'</td>';
          html += '<td style="padding:6px 8px;font-size:11px;color:#64748b">'+_escHTML(p.motivo)+'</td>';
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      }
      html += '</div>';

      // Vista sin ventas
      if(sinVentas.length){
        html += '<div id="plLargo-vista-sin" style="display:none">';
        html += '<div style="background:#fef3c7;border:1px solid #fcd34d;padding:12px;border-radius:8px;margin-bottom:12px;color:#78350f;font-size:12px">Estos SKUs están activos pero sin ventas detectadas en Shopify (velocidad &lt; 0.01 u/día). El sistema NO los planeó. Considera marcarlos como descontinuados o revisar la conexión Shopify.</div>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#fef3c7"><tr><th style="padding:8px;text-align:left">Producto</th><th style="padding:8px;text-align:right">Stock</th><th style="padding:8px;text-align:left">Razón</th></tr></thead><tbody>';
        sinVentas.forEach(function(s){
          html += '<tr style="border-top:1px solid #fde68a"><td style="padding:6px 8px"><b>'+_escHTML(s.producto)+'</b></td><td style="padding:6px 8px;text-align:right">'+s.stock_inicial+'u</td><td style="padding:6px 8px;color:#78350f">'+_escHTML(s.razon)+'</td></tr>';
        });
        html += '</tbody></table></div>';
      }

      html += '</div>';
      modal.innerHTML = html;
    } catch(e){
      modal.innerHTML = '<div style="background:#fff;border-radius:12px;padding:30px;color:#dc2626">Error: '+(e.message||'desconocido')+'<br><button onclick="this.closest(\\'div[style*=fixed]\\').remove()" style="margin-top:14px;padding:6px 14px">Cerrar</button></div>';
    }
  }

  function planLargoTab(t){
    ['mes','sku','lista','sin'].forEach(function(name){
      var v = document.getElementById('plLargo-vista-'+name);
      if(v) v.style.display = (name===t)?'block':'none';
    });
    var btns = document.querySelectorAll('.plLargo-tab');
    btns.forEach(function(b){
      var a = b.getAttribute('data-tab');
      if(a===t){ b.style.background='#0891b2'; b.style.color='#fff'; }
      else { b.style.background='#f1f5f9'; b.style.color='#475569'; }
    });
  }

  function planLargoCSV(){
    var d = window._planLargoData;
    if(!d || !d.producciones){ alert('No hay datos cargados'); return; }
    var rows = [['Fecha','Día','Producto','Lote_kg','Unidades','Stock_antes','Stock_después','Velocidad_día','Motivo','Forzado']];
    d.producciones.forEach(function(p){
      rows.push([p.fecha,p.dia_semana,p.producto,p.lote_kg,p.unidades_lote,p.stock_antes,p.stock_despues,p.velocidad_dia,(p.motivo||'').replace(/[\\n\\r,;]/g,' '),p.forzado_capacidad?'SI':'']);
    });
    var csv = rows.map(function(r){return r.map(function(c){var s=String(c==null?'':c);return /[,;"\\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;}).join(',');}).join('\\n');
    var blob = new Blob([csv], {type:'text/csv;charset=utf-8'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'plan_'+d.horizonte_meses+'meses_'+d.fecha_inicio+'.csv';
    a.click();
  }

  async function recDescontinuar(producto){
    var razon = prompt('¿Por qué descontinuar "'+producto+'"?\\n(El sistema dejará de programar producción para este SKU)', 'Ya no se produce');
    if(razon === null) return;
    try {
      var r1 = await fetch('/api/auto-plan/configs/sku');
      var d1 = await r1.json();
      var cfg = (d1.configs||[]).find(function(x){return (x.producto_nombre||'').trim().toUpperCase() === producto.trim().toUpperCase();});
      if(!cfg){ alert('SKU no encontrado'); return; }
      var r = await fetch('/api/planta/sku/'+cfg.id+'/estado', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado:'descontinuado', razon: razon})
      });
      if(r.ok){ _toast('✓ '+producto+' descontinuado', 1); planV2CargarRecomendaciones(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  async function recReactivar(producto){
    if(!confirm('¿Reactivar "'+producto+'"? El sistema volverá a programarlo.')) return;
    try {
      var r1 = await fetch('/api/auto-plan/configs/sku');
      var d1 = await r1.json();
      var cfg = (d1.configs||[]).find(function(x){return (x.producto_nombre||'').trim().toUpperCase() === producto.trim().toUpperCase();});
      if(!cfg){ alert('SKU no encontrado'); return; }
      var r = await fetch('/api/planta/sku/'+cfg.id+'/estado', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({estado:'activo'})
      });
      if(r.ok){ _toast('✓ '+producto+' reactivado', 1); planV2CargarRecomendaciones(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  async function planV2CargarRecomendaciones(){
    var box = document.getElementById('pv2-recomendaciones-wrap');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8">🧠 Calculando recomendaciones inteligentes...</div>';
    try {
      var r = await fetch('/api/planta/recomendaciones');
      var d = await r.json();
      var recs = d.recomendaciones || [];
      var k = d.kpis || {};
      // Filtrar: SOLO mostrar accionables (críticas, altas, medias, bajas) y OK
      // Sin_ventas / baja_rotacion / inactivo van colapsados al final
      var accionables = recs.filter(function(x){return ['critica','alta','media','baja'].indexOf(x.urgencia) >= 0;});
      var inactivos = recs.filter(function(x){return ['sin_ventas','baja_rotacion','inactivo'].indexOf(x.urgencia) >= 0;});
      var resumen = '';
      if(k.criticas) resumen += '<span style="background:#dc2626;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800;margin-right:6px">🚨 '+k.criticas+' CRÍTICAS</span>';
      if(k.altas) resumen += '<span style="background:#d97706;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:800;margin-right:6px">⚠ '+k.altas+' altas</span>';
      if(k.medias) resumen += '<span style="background:#0891b2;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:700;margin-right:6px">'+k.medias+' medias</span>';
      if(k.bajas) resumen += '<span style="background:#7c3aed;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-right:6px">'+k.bajas+' bajas</span>';
      if(k.innecesarias) resumen += '<span style="background:#15803d;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-right:6px">✓ '+k.innecesarias+' OK</span>';
      var inact = (k.sin_ventas||0)+(k.baja_rotacion||0)+(k.inactivos||0);
      if(inact) resumen += '<span style="background:#475569;color:#fff;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600">⊗ '+inact+' inactivos</span>';
      var distInfo = d.distribucion || {};
      var distrChip = distInfo.patron ? '<div style="font-size:10px;color:#94a3b8;margin-top:6px">📅 Distribución: <b>'+distInfo.patron+'</b> · '+(distInfo.razon||'')+'</div>' : '';
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">'
        +'<div style="background:linear-gradient(135deg,#1e293b,#0f172a);color:#fff;padding:14px 18px">'
        +'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">'
        +'<div><h3 style="margin:0;color:#fff;font-size:16px">🧠 Recomendaciones Inteligentes</h3><div style="font-size:11px;color:#cbd5e1;margin-top:2px">Stock Shopify + Pipeline (Calendar 14d) + Velocidad ventas → fecha óptima</div></div>'
        +'<div>'+resumen+'</div>'
        +'</div>'
        + distrChip
        +'</div>';
      if(!accionables.length){
        html += '<div style="padding:30px;text-align:center;color:#15803d;font-size:14px">✅ Todos los SKUs cubiertos · ningún producto requiere acción inmediata</div>';
      } else {
        html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
          +'<thead style="background:#f9fafb;border-bottom:2px solid #e5e7eb"><tr>'
          +'<th style="padding:10px 12px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Stock</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Pipeline</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Total</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Días</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Cadencia</th>'
          +'<th style="padding:10px 8px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Lote típ.</th>'
          +'<th style="padding:10px 12px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Recomendación</th>'
          +'</tr></thead><tbody>';
        accionables.forEach(function(r){
          var urgCol = {critica:'#dc2626',alta:'#d97706',media:'#0891b2',baja:'#7c3aed'}[r.urgencia] || '#64748b';
          var fechaTxt = '—';
          if(r.fecha_proxima){
            try {
              var dia = new Date(r.fecha_proxima+'T00:00:00').toLocaleDateString('es-CO',{weekday:'short',day:'numeric',month:'short'});
              fechaTxt = dia;
            } catch(e){ fechaTxt = r.fecha_proxima; }
          }
          html += '<tr style="border-top:1px solid #f1f5f9;background:'+(r.urgencia==='critica'?'#fef2f2':r.urgencia==='alta'?'#fffbeb':'#fff')+'">'
            +'<td style="padding:8px 12px"><b style="color:#0f172a">'+_escHTML(r.producto)+'</b><br><span style="font-size:10px;color:#64748b">'+r.velocidad_dia+' u/día</span></td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace">'+r.stock_shopify+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;color:#0891b2;font-weight:600">'+(r.pipeline_unidades>0?'+'+r.pipeline_unidades:'—')+'<br><span style="font-size:9px;color:#64748b">'+r.pipeline_kg+'kg</span></td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-weight:700">'+r.stock_total_unidades+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-weight:800;color:'+urgCol+'">'+r.dias_alcance+'d</td>'
            +'<td style="padding:8px;text-align:right;font-size:11px;color:#64748b">'+(r.cadencia_historica_dias?r.cadencia_historica_dias+'d hist':r.cadencia_configurada?r.cadencia_configurada+'d cfg':'—')+'</td>'
            +'<td style="padding:8px;text-align:right;font-family:monospace;font-size:11px">'+r.lote_tipico_kg+'kg</td>'
            +'<td style="padding:8px 12px"><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="background:'+urgCol+';color:#fff;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:800;text-transform:uppercase">'+r.urgencia+'</span><b style="color:#0f172a;font-size:12px;text-transform:capitalize">'+_escHTML(fechaTxt)+'</b></div><div style="font-size:11px;color:#475569;margin-top:4px">'+_escHTML(r.razon)+'</div><div style="margin-top:6px"><button onclick="recDescontinuar(\\''+_escAttr(r.producto)+'\\')" style="background:#fff;color:#dc2626;border:1px solid #dc2626;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;cursor:pointer">⊗ Descontinuar</button></div></td>'
            +'</tr>';
        });
        html += '</tbody></table></div>';
      }
      // Sección OK (colapsable)
      var oks = recs.filter(function(x){return x.urgencia==='innecesaria'});
      if(oks.length){
        html += '<details style="border-top:1px solid #e5e7eb;padding:8px 16px"><summary style="cursor:pointer;color:#15803d;font-size:12px;font-weight:600">✅ '+oks.length+' SKUs cubiertos (no requieren acción)</summary>'
          +'<div style="margin-top:8px;font-size:11px;color:#64748b;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:6px">';
        oks.forEach(function(r){
          html += '<div style="background:#f0fdf4;padding:5px 8px;border-radius:4px;border-left:3px solid #15803d">'
            +'<b>'+_escHTML(r.producto)+'</b><br><span style="color:#166534">stock '+r.dias_alcance+'d · '+r.stock_total_unidades+'u total</span></div>';
        });
        html += '</div></details>';
      }
      // Sección INACTIVOS / SIN VENTAS / DESCONTINUADOS (colapsada)
      if(inactivos.length){
        html += '<details style="border-top:1px solid #e5e7eb;padding:8px 16px;background:#f8fafc"><summary style="cursor:pointer;color:#64748b;font-size:12px;font-weight:600">⊗ '+inactivos.length+' SKUs inactivos / sin ventas (no se programa producción)</summary>'
          +'<div style="margin-top:8px;font-size:11px;color:#64748b">';
        inactivos.forEach(function(r){
          var label = r.urgencia==='sin_ventas'?'sin ventas':(r.urgencia==='baja_rotacion'?'baja rotación':r.estado_sku||r.urgencia);
          html += '<div style="display:flex;justify-content:space-between;align-items:center;background:#fff;padding:6px 10px;border-radius:5px;border-left:3px solid #94a3b8;margin-bottom:4px">'
            +'<div><b>'+_escHTML(r.producto)+'</b><br><span style="color:#94a3b8;font-size:10px">'+_escHTML(label)+' · '+_escHTML(r.razon||'')+'</span></div>'
            +'<button onclick="recReactivar(\\''+_escAttr(r.producto)+'\\')" style="background:#fff;color:#15803d;border:1px solid #15803d;padding:3px 10px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer">↻ Reactivar</button>'
            +'</div>';
        });
        html += '</div></details>';
      }
      html += '</div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  async function planV2CargarCalendarStatus(){
    var box = document.getElementById('pv2-calendar-status');
    if(!box) return;
    try {
      var r = await fetch('/api/planta/calendar-debug');
      var d = await r.json();
      if(d.total_eventos === 0){
        box.style.display = 'block';
        box.innerHTML = '⚠ <b>Calendar vacío</b> — verifica GCAL_ICAL_URL en Render. <a href="#" onclick="switchProgTab(\\'config\\');setTimeout(function(){cfgSubtab(\\'calendar\\')},150);return false" style="color:#fff;text-decoration:underline">Ir a Configuración</a>';
        return;
      }
      box.style.display = 'block';
      box.innerHTML = '📆 Calendar: <b>'+d.total_eventos+'</b> eventos · ✓ <b style="color:#86efac">'+d.matcheados+'</b> matcheados con productos · '
        +(d.sin_match_aceptable ? '? <b style="color:#fbbf24">'+d.sin_match_aceptable+'</b> sin match — '+'<a href="#" onclick="switchProgTab(\\'config\\');setTimeout(function(){cfgSubtab(\\'calendar\\')},150);return false" style="color:#fff;text-decoration:underline">configurar aliases</a>' : '<span style="color:#86efac">100% identificados</span>')
        +' · ⚖ <b>'+d.con_kg_detectados+'</b> con kg parseados';
    } catch(e){ /* silent */ }
  }

  async function planV2CargarCobertura(){
    var box = document.getElementById('pv2-cobertura');
    if(!box) return;
    var meses = parseFloat(_PV2_HORIZONTE);
    var dias = meses < 1 ? 14 : Math.round(meses * 30);
    try {
      var r = await fetch('/api/planta/kpi-cobertura?dias='+dias);
      var d = await r.json();
      var pct = d.cobertura_pct || 0;
      var icon = pct >= 90 ? '✅' : (pct >= 60 ? '⚠️' : '🔴');
      var col = pct >= 90 ? '#10b981' : (pct >= 60 ? '#fbbf24' : '#fca5a5');
      var horizonteLabel = meses < 1 ? 'semana' : (meses+(meses===1?' mes':' meses'));
      box.innerHTML = '<span style="color:'+col+';font-weight:800">'+icon+' '+pct+'% cobertura ('+horizonteLabel+')</span> · '
        +'<b>'+d.en_plan+' / '+d.total_skus+' SKUs</b> con producción en el horizonte (BD + Google Calendar) · '
        +(d.sin_plan && d.sin_plan.length ? '<span style="color:#fca5a5">'+d.sin_plan.length+' SIN plan: '+_escHTML(d.sin_plan.slice(0,3).join(', '))+(d.sin_plan.length>3?'…':'')+'</span>' : '<span style="color:#10b981">Todos los SKUs cubiertos</span>');
    } catch(e){ /* silent */ }
  }

  function abrirNuevoProducto(){
    ['np-nombre','np-lote','np-cadencia','np-fecha','np-lotes'].forEach(function(id){var e=document.getElementById(id); if(e) e.value=(id==='np-merma'?'5':(id==='np-lotes'?'1':''));});
    document.getElementById('np-merma').value = '5';
    document.getElementById('np-categoria').value = '';
    document.getElementById('np-prioritario').checked = false;
    document.getElementById('np-prio-detalle').style.display = 'none';
    document.getElementById('modal-nuevo-producto').style.display = 'flex';
    // Listener checkbox
    var chk = document.getElementById('np-prioritario');
    chk.onchange = function(){
      document.getElementById('np-prio-detalle').style.display = chk.checked ? 'block' : 'none';
    };
  }

  async function guardarNuevoProducto(){
    var body = {
      producto_nombre: (document.getElementById('np-nombre').value||'').trim().toUpperCase(),
      lote_size_kg: parseFloat(document.getElementById('np-lote').value),
      categoria: document.getElementById('np-categoria').value || null,
      cadencia_dias: parseInt(document.getElementById('np-cadencia').value) || null,
      merma_pct: parseFloat(document.getElementById('np-merma').value) || 5,
      prioritario: document.getElementById('np-prioritario').checked,
      fecha_primera_prod: document.getElementById('np-fecha').value || null,
      lotes_inicial: parseInt(document.getElementById('np-lotes').value) || 1,
    };
    if(!body.producto_nombre){ alert('Nombre requerido'); return; }
    if(!body.lote_size_kg || body.lote_size_kg <= 0){ alert('Tamaño lote requerido'); return; }
    try {
      var r = await fetch('/api/planta/producto-nuevo', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-nuevo-producto').style.display='none';
      var msg = '✓ '+body.producto_nombre+' creado';
      if(d.produccion_creada_id) msg += ' (producción #'+d.produccion_creada_id+')';
      _toast(msg, 1);
      planV2Cargar();
      planV2CargarCobertura();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function planV2DetectarCambios(){
    try {
      var r = await fetch('/api/planta/detectar-cambios-demanda');
      var d = await r.json();
      var cambios = d.cambios || [];
      var box = document.getElementById('pv2-comprar-ya');
      if(!cambios.length) return;
      // Renderizar banner de cambios encima del de "comprar ya"
      var existing = document.getElementById('pv2-cambios-demanda');
      if(existing) existing.remove();
      var banner = document.createElement('div');
      banner.id = 'pv2-cambios-demanda';
      banner.style.cssText = 'background:linear-gradient(135deg,#fef3c7,#fde68a);border:2px solid #d97706;border-radius:12px;padding:14px 18px;margin-bottom:14px';
      banner.innerHTML = '<h3 style="margin:0 0 8px;color:#92400e;font-size:14px">📈 '+cambios.length+' cambio(s) de demanda detectado(s)</h3>'
        + '<div style="font-size:12px;color:#78350f;margin-bottom:8px">El sistema detectó que las ventas cambiaron significativamente. Revisa si ajustar el plan:</div>'
        + cambios.map(function(c, i){
          var icono = c.tipo === 'aumento' ? '📈' : '📉';
          var color = c.tipo === 'aumento' ? '#dc2626' : '#0891b2';
          return '<div style="background:#fff;border:1px solid #fbbf24;border-radius:8px;padding:10px 12px;margin-top:6px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
            + '<div style="font-size:12px"><b>'+icono+' '+_escHTML(c.producto)+'</b> · <span style="color:'+color+';font-weight:700">'+(c.cambio_pct>0?'+':'')+c.cambio_pct+'%</span> ('+c.velocidad_base.toFixed(1)+'→'+c.velocidad_reciente.toFixed(1)+' u/d)<br><span style="color:#64748b;font-size:11px">'+_escHTML(c.recomendacion||'Sin recomendación específica')+'</span></div>'
            + (c.fecha_sugerida && c.proxima_produccion_id
              ? '<button onclick="aceptarRecomendacion('+c.proxima_produccion_id+',\\''+c.fecha_sugerida+'\\')" style="background:#0f766e;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap">✓ Aceptar</button>'
              : '<span style="color:#94a3b8;font-size:11px">Sin acción</span>')
            + '</div>';
        }).join('');
      box.parentNode.insertBefore(banner, box);
    } catch(e){ /* silent */ }
  }

  async function aceptarRecomendacion(prodId, nuevaFecha){
    if(!confirm('¿Mover esta producción a '+nuevaFecha+'?')) return;
    try {
      var r = await fetch('/api/planta/produccion/'+prodId+'/aceptar-recomendacion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({nueva_fecha: nuevaFecha})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Producción movida', 1);
      planV2Init();
    } catch(e){ alert('Error: '+e.message); }
  }

  function planV2Horizonte(meses){
    _PV2_HORIZONTE = meses;
    document.querySelectorAll('.phz-btn').forEach(function(b){
      var act = b.dataset.meses === meses;
      b.style.background = act ? '#fff' : 'rgba(255,255,255,.18)';
      b.style.color = act ? '#0f766e' : '#fff';
    });
    planV2Cargar();
    planV2CargarCobertura();
    // Recomendaciones siempre las mismas (no dependen de horizonte)
  }

  async function planV2Cargar(){
    var vista = document.getElementById('pv2-vista');
    var kpis = document.getElementById('pv2-kpis');
    if(!vista) return;
    vista.innerHTML = '<div style="text-align:center;padding:40px;color:#94a3b8">Cargando plan...</div>';
    var meses = parseFloat(_PV2_HORIZONTE);
    try {
      // Para horizonte ≤ 2 meses: pintar grid calendario visual ARRIBA + cards abajo
      var calendarHtml = '';
      if(meses <= 2){
        try {
          var diasGrid = meses < 1 ? 14 : Math.round(meses * 30);
          var calR = await fetch('/api/planta/calendar-eventos-plan?dias='+diasGrid);
          var calD = await calR.json();
          calendarHtml = planV2RenderCalendarGrid(calD.events || [], diasGrid);
        } catch(e){ /* sin calendar grid si falla */ }
      }
      if(meses < 1){
        var r = await fetch('/api/planta/plan-semanal-v2?dias=14');
        var d = await r.json();
        _PV2_DATA = d;
        planV2RenderSemanaV2(d);
        if(calendarHtml) vista.innerHTML = calendarHtml + vista.innerHTML;
      } else {
        var r = await fetch('/api/planta/forecast?meses='+Math.round(meses));
        var d = await r.json();
        _PV2_DATA = d;
        planV2RenderForecast(d, Math.round(meses));
        if(calendarHtml) vista.innerHTML = calendarHtml + vista.innerHTML;
      }
    } catch(e){
      vista.innerHTML = '<div style="color:#dc2626;padding:20px">Error: '+e.message+'</div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════
  // VISTA CALENDARIO GRID — pinta los eventos del Calendar como grid mensual
  // ════════════════════════════════════════════════════════════════════
  function planV2RenderCalendarGrid(events, diasHorizonte){
    if(!events || !events.length){
      return '<div style="background:#f8fafc;border:1px dashed #cbd5e1;border-radius:10px;padding:18px;margin-bottom:14px;text-align:center;color:#94a3b8;font-size:13px">📅 Sin eventos del Calendar en los próximos '+diasHorizonte+' días</div>';
    }
    // Agrupar eventos por fecha
    var porFecha = {};
    events.forEach(function(e){
      if(!porFecha[e.fecha]) porFecha[e.fecha] = [];
      porFecha[e.fecha].push(e);
    });
    // Determinar rango: hoy + N días
    var hoy = new Date();
    hoy.setHours(0,0,0,0);
    var fin = new Date(hoy.getTime() + diasHorizonte*86400000);
    // Ajustar inicio al lunes anterior, fin al domingo siguiente
    var inicio = new Date(hoy);
    var dowInicio = (inicio.getDay() + 6) % 7;  // 0=Mon
    inicio.setDate(inicio.getDate() - dowInicio);
    var dowFin = (fin.getDay() + 6) % 7;
    fin.setDate(fin.getDate() + (6 - dowFin));

    var nombreMeses = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
    var nombreDias = ['L','M','M','J','V','S','D'];

    var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;margin-bottom:14px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">';
    html += '<b style="color:#0f172a;font-size:14px">📅 Calendario de Producción</b>';
    html += '<span style="font-size:11px;color:#64748b">'+events.length+' eventos · '+inicio.toLocaleDateString('es-CO',{day:'numeric',month:'short'})+' → '+fin.toLocaleDateString('es-CO',{day:'numeric',month:'short'})+'</span>';
    html += '</div>';

    // Headers de días
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:6px">';
    nombreDias.forEach(function(d,i){
      var col = i>=5 ? '#94a3b8' : '#475569';
      html += '<div style="text-align:center;font-size:10px;color:'+col+';font-weight:700;text-transform:uppercase;padding:4px">'+d+'</div>';
    });
    html += '</div>';

    // Grid de días
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px">';
    var cur = new Date(inicio);
    var hoyISO = new Date().toISOString().slice(0,10);
    while(cur <= fin){
      var iso = cur.toISOString().slice(0,10);
      var dow = (cur.getDay() + 6) % 7;
      var esWeekend = dow >= 5;
      var esHoy = iso === hoyISO;
      var dentroRango = cur >= hoy && cur <= new Date(hoy.getTime() + diasHorizonte*86400000);
      var evs = porFecha[iso] || [];
      var bg = esHoy ? '#fef3c7' : esWeekend ? '#f8fafc' : (dentroRango?'#fff':'#f1f5f9');
      var border = esHoy ? '2px solid #f59e0b' : '1px solid #e2e8f0';
      html += '<div style="background:'+bg+';border:'+border+';border-radius:6px;min-height:80px;padding:5px;font-size:10px;'+(dentroRango?'':'opacity:.5')+'">';
      html += '<div style="font-weight:700;color:'+(esHoy?'#92400e':esWeekend?'#94a3b8':'#0f172a')+';margin-bottom:3px">'+cur.getDate()+(cur.getDate()===1?' '+nombreMeses[cur.getMonth()]:'')+'</div>';
      evs.slice(0,3).forEach(function(e){
        var titulo = (e.titulo||'').replace(/[🌿💋🧴🧬🍊🚿💄🆕💡🔬✨🧪☕🌿💫📦👁️💧🛍️🏖️]/g,'').trim();
        html += '<div title="'+_escHTML(e.titulo||'')+'" style="background:rgba(99,102,241,.15);color:#3730a3;padding:2px 4px;border-radius:3px;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9px">'+_escHTML((e.titulo||'').slice(0,18))+'</div>';
      });
      if(evs.length > 3) html += '<div style="font-size:9px;color:#64748b">+'+(evs.length-3)+' más</div>';
      html += '</div>';
      cur.setDate(cur.getDate() + 1);
    }
    html += '</div>';
    html += '<div style="margin-top:8px;font-size:10px;color:#64748b;text-align:center">⬛ hoy · ⬜ fin de semana · 💜 evento Calendar</div>';
    html += '</div>';
    return html;
  }

  function planV2RenderSemanaV2(d){
    var kpis = document.getElementById('pv2-kpis');
    var k = d.kpis || {};
    var status = d.auto_plan_status || {};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Próximas 14d</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Confirmadas</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.desde_bd||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">🔮 Proyectadas</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.proyectadas||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(status.horas_desde_run<24?'#15803d':'#d97706')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Auto-Plan</div><div style="font-size:14px;font-weight:700;color:'+(status.horas_desde_run<24?'#15803d':'#d97706')+';margin-top:4px">'+(status.horas_desde_run!=null ? 'hace '+status.horas_desde_run+'h' : 'nunca corrió')+'</div></div>';

    document.getElementById('pv2-comprar-ya').style.display = 'none';

    var vista = document.getElementById('pv2-vista');
    var items = d.items || [];

    // Banner si todas son proyectadas
    var banner = '';
    if(k.desde_bd === 0 && k.proyectadas > 0){
      banner = '<div style="background:#f3e8ff;border:1px solid #d8b4fe;border-radius:10px;padding:14px 18px;margin-bottom:14px;color:#6b21a8;font-size:13px">'
        +'<b>🔮 Plan proyectado automáticamente</b> · Se calculó desde Shopify + cadencias. '
        +'Ejecuta <b>🔥 Auto-Plan AHORA</b> para confirmar y crear los registros, o haz click en cada producción para confirmarla individual.'
        +'</div>';
    } else if(k.desde_bd > 0 && k.proyectadas === 0 && status.horas_desde_run > 24){
      banner = '<div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:10px;padding:14px 18px;margin-bottom:14px;color:#92400e;font-size:13px">'
        +'⚠ El Auto-Plan no se ha ejecutado en '+status.horas_desde_run+'h. <b>Ejecuta AHORA</b> para refrescar con datos actuales de Shopify.'
        +'</div>';
    }

    if(!items.length){
      vista.innerHTML = banner + '<div style="background:#fef3c7;padding:30px;border-radius:10px;text-align:center;color:#92400e;font-size:14px">⚠ Sin producciones próximas. Ejecuta <b>Auto-Plan</b> para que el sistema calcule el plan desde Shopify.</div>';
      return;
    }

    vista.innerHTML = banner + '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">'
      + items.map(function(it){
        var esProy = it.origen === 'proyeccion';
        var borderCol = esProy ? '#7c3aed' : '#e2e8f0';
        var img = it.imagen_url
          ? '<img src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:110px;object-fit:cover" alt="">'
          : '<div style="width:100%;height:110px;background:linear-gradient(135deg,'+(esProy?'#7c3aed,#dc2626':'#0f766e,#0891b2')+');display:flex;align-items:center;justify-content:center;color:#fff;font-size:32px">📦</div>';
        var fechaTxt = '';
        try { fechaTxt = new Date(it.fecha_programada+'T00:00:00').toLocaleDateString('es-CO',{weekday:'short',day:'numeric',month:'short'}); } catch(e){ fechaTxt = it.fecha_programada; }
        var idAttr = it.produccion_id || 0;
        return '<div data-prod-id="'+idAttr+'" data-producto="'+_escAttr(it.producto)+'" data-fecha="'+_escAttr(it.fecha_programada)+'" data-kg="'+(it.kg||0)+'" style="background:#fff;border:2px solid '+borderCol+';border-radius:10px;overflow:hidden;transition:transform .12s">'
          + '<div onclick="' + (esProy ? 'confirmarProyeccion(this.parentNode)' : 'abrirPlanSemModal('+idAttr+')') + '" style="cursor:pointer">' + img + '</div>'
          +'<div style="padding:10px 12px;position:relative">'
          + (esProy ? '<div style="position:absolute;top:-12px;right:8px;background:#7c3aed;color:#fff;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:800;letter-spacing:.5px">🔮 PROYECTADA</div>' : '')
          +'<b style="color:#0f172a;font-size:13px">'+_escHTML(it.producto)+'</b>'
          +'<div style="font-size:11px;color:#64748b;margin-top:2px;text-transform:capitalize">📅 '+_escHTML(fechaTxt)+' · '+(it.kg||0).toFixed(0)+'kg</div>'
          + (esProy
              ? '<div style="font-size:11px;color:#7c3aed;margin-top:6px;font-weight:600">👆 Click para confirmar</div>'
              : (it.area_nombre ? '<div style="font-size:11px;color:#64748b;margin-top:4px">🏭 '+_escHTML(it.area_nombre)+'</div>' : '<div style="font-size:11px;color:#dc2626;margin-top:4px">⚠ Sin área asignada</div>'))
          + (!esProy && idAttr ? '<div style="display:flex;gap:4px;margin-top:8px;border-top:1px solid #e5e7eb;padding-top:8px">'
              +'<button onclick="event.stopPropagation();editarLoteModal('+idAttr+',\\''+_escAttr(it.producto)+'\\','+(it.kg||0)+')" style="flex:1;background:#fff;color:#0891b2;border:1px solid #0891b2;padding:5px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✏️ Editar lote</button>'
              +'<button onclick="event.stopPropagation();eliminarYReplanificar('+idAttr+',\\''+_escAttr(it.producto)+'\\')" style="flex:1;background:#fff;color:#dc2626;border:1px solid #dc2626;padding:5px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">🗑 Eliminar</button>'
              +'</div>' : '')
          +'</div></div>';
      }).join('')
      +'</div>';
  }

  async function confirmarProyeccion(card){
    var producto = card.dataset.producto;
    var fecha = card.dataset.fecha;
    var kg = parseFloat(card.dataset.kg) || 0;
    if(!confirm('¿Confirmar producción de "'+producto+'" para '+fecha+'?\\n\\nSe creará en el calendario y aparecerá en Pre-flight.')) return;
    try {
      var r = await fetch('/api/planta/confirmar-proyeccion', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({producto: producto, fecha_programada: fecha, kg: kg})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'no se pudo confirmar')); return; }
      _toast(d.ya_existia ? 'Ya estaba creada' : '✓ Producción confirmada', 1);
      planV2Cargar();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function eliminarYReplanificar(prodId, producto){
    var motivo = prompt('¿Por qué eliminas esta producción de "'+producto+'"?\\n\\n(El sistema propondrá automáticamente otra fecha en su lugar según cadencia)', 'Ya producida');
    if(motivo === null) return;
    try {
      var r = await fetch('/api/planta/produccion/'+prodId+'/eliminar-y-replanificar', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({motivo: motivo})
      });
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      _toast('✓ Eliminada · nueva sugerida para '+d.nueva_fecha, 1);
      planV2Cargar();
    } catch(e){ alert('Error: '+e.message); }
  }

  function planV2Descargar(){
    var meses = parseFloat(_PV2_HORIZONTE);
    if(meses < 1) meses = 1;
    window.open('/api/planta/plan/exportar?meses='+Math.round(meses)+'&formato=xlsx', '_blank');
  }

  // ════════════════════════════════════════════════════════════════════════
  // MAQUILA · pedidos de clientes que se suman al plan
  // ════════════════════════════════════════════════════════════════════════
  var _MQ_CLIENTES = [];
  var _MQ_PRODUCTOS = [];

  async function maquilaInit(){
    cargarClientesMaquila();
    cargarPedidosMaquila();
  }

  async function cargarClientesMaquila(){
    try {
      var r = await fetch('/api/maquila/clientes');
      var d = await r.json();
      _MQ_CLIENTES = d.clientes || [];
    } catch(e){}
  }

  async function cargarPedidosMaquila(){
    var box = document.getElementById('mq-pedidos');
    var kpis = document.getElementById('mq-kpis');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/maquila/pedidos?estado=todos');
      var d = await r.json();
      var items = d.pedidos || [];
      var pend = items.filter(function(x){return x.estado==='recibido'}).length;
      var plan = items.filter(function(x){return x.estado==='planificado'}).length;
      var enProd = items.filter(function(x){return x.estado==='en_produccion'}).length;
      var entreg = items.filter(function(x){return x.estado==='entregado'}).length;
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Recibidos</div><div style="font-size:26px;font-weight:800;color:#d97706">'+pend+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Planificados</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+plan+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">En producción</div><div style="font-size:26px;font-weight:800;color:#0891b2">'+enProd+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Entregados</div><div style="font-size:26px;font-weight:800;color:#15803d">'+entreg+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #1a4a7a;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Clientes</div><div style="font-size:26px;font-weight:800;color:#1a4a7a">'+_MQ_CLIENTES.length+'</div></div>';

      if(!items.length){
        box.innerHTML = '<div style="background:#f8fafc;padding:30px;border-radius:10px;text-align:center;color:#94a3b8">Sin pedidos de maquila. Crea uno con "+ Nuevo pedido".</div>';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
      html += '<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">N°</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Cliente</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Unidades</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Kg</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Entrega</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producción</th>'
        +'<th style="padding:8px 10px"></th>'
        +'</tr></thead><tbody>';
      items.forEach(function(p){
        var estCol = {recibido:'#d97706',planificado:'#7c3aed',en_produccion:'#0891b2',listo_entrega:'#1a4a7a',entregado:'#15803d',cancelado:'#94a3b8'}[p.estado] || '#475569';
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px;font-family:monospace;font-size:11px"><b>'+_escHTML(p.numero)+'</b></td>'
          +'<td style="padding:7px 10px"><b>'+_escHTML(p.cliente_nombre||'')+'</b></td>'
          +'<td style="padding:7px 10px">'+_escHTML(p.producto_nombre||'')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(p.unidades||0).toLocaleString('es-CO')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:#64748b">'+(p.kg_estimados ? p.kg_estimados.toFixed(1) : '—')+'</td>'
          +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.fecha_entrega_objetivo||'—')+'</td>'
          +'<td style="padding:7px 10px;text-align:center"><span style="background:'+estCol+'22;color:'+estCol+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase">'+_escHTML(p.estado)+'</span></td>'
          +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+(p.produccion_id ? '#'+p.produccion_id+(p.produccion_fecha?' · '+_escHTML(p.produccion_fecha):'') : '—')+'</td>'
          +'<td style="padding:7px 10px;text-align:right">'+(p.estado==='recibido' || p.estado==='planificado' ? '<button onclick="cancelarPedidoMaquila('+p.id+')" style="background:#fff;color:#dc2626;border:1px solid #dc2626;padding:3px 8px;border-radius:5px;font-size:10px;font-weight:700;cursor:pointer">✕</button>' : '')+'</td>'
          +'</tr>';
      });
      html += '</tbody></table></div>';
      // Mensaje educativo
      html += '<div style="background:#f0f9ff;border:1px solid #7dd3fc;border-radius:10px;padding:12px 16px;margin-top:14px;font-size:12px;color:#0369a1">💡 <b>Cómo funciona:</b> Los pedidos en estado "recibido" se SUMAN automáticamente al lote de Animus la próxima vez que el Auto-Plan corra. Si Kelly Guerra pide 500 unid de Suero AH y Animus va a producir 90kg → el lote total será 90kg + lo necesario para esas 500 unid.</div>';
      box.innerHTML = html;
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  function abrirNuevoPedido(){
    if(!_MQ_CLIENTES.length){ alert('Primero crea un cliente con "+ Cliente"'); return; }
    var sel = document.getElementById('mq-cliente');
    sel.innerHTML = '<option value="">— elegir cliente —</option>'
      + _MQ_CLIENTES.map(function(c){return '<option value="'+c.id+'">'+_escHTML(c.nombre)+(c.comparte_formula_con?' (fórmula '+_escHTML(c.comparte_formula_con)+')':'')+'</option>';}).join('');
    var sp = document.getElementById('mq-producto');
    sp.innerHTML = '<option value="">— elegir producto —</option>'
      + (_presProductos||[]).map(function(p){return '<option value="'+_escAttr(p.producto_nombre)+'">'+_escHTML(p.producto_nombre)+'</option>';}).join('');
    if(!(_presProductos||[]).length){
      // Cargar productos si no están cargados
      fetch('/api/planta/presentaciones/productos-disponibles').then(function(r){return r.json();}).then(function(d){
        _presProductos = d.productos || [];
        sp.innerHTML = '<option value="">— elegir producto —</option>'
          + _presProductos.map(function(p){return '<option value="'+_escAttr(p.producto_nombre)+'">'+_escHTML(p.producto_nombre)+'</option>';}).join('');
      });
    }
    ['mq-unidades','mq-kg','mq-fecha','mq-obs'].forEach(function(id){var e=document.getElementById(id); if(e) e.value='';});
    document.getElementById('modal-mq-pedido').style.display = 'flex';
  }

  async function guardarPedidoMaquila(){
    var body = {
      cliente_id: parseInt(document.getElementById('mq-cliente').value),
      producto_nombre: document.getElementById('mq-producto').value,
      unidades: parseInt(document.getElementById('mq-unidades').value),
      kg_estimados: parseFloat(document.getElementById('mq-kg').value)||null,
      fecha_entrega_objetivo: document.getElementById('mq-fecha').value,
      observaciones: document.getElementById('mq-obs').value,
    };
    if(!body.cliente_id || !body.producto_nombre || !body.unidades){
      alert('Cliente, producto y unidades son requeridos'); return;
    }
    try {
      var r = await fetch('/api/maquila/pedidos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-mq-pedido').style.display='none';
      _toast('✓ Pedido '+d.numero+' creado', 1);
      cargarPedidosMaquila();
    } catch(e){ alert('Error: '+e.message); }
  }

  function abrirNuevoCliente(){
    ['mc-nombre','mc-email','mc-tel','mc-comparte'].forEach(function(id){var e=document.getElementById(id); if(e) e.value='';});
    document.getElementById('modal-mq-cliente').style.display = 'flex';
  }

  async function guardarClienteMaquila(){
    var body = {
      nombre: document.getElementById('mc-nombre').value.trim(),
      email: document.getElementById('mc-email').value.trim(),
      telefono: document.getElementById('mc-tel').value.trim(),
      comparte_formula_con: document.getElementById('mc-comparte').value.trim(),
    };
    if(!body.nombre){ alert('Nombre requerido'); return; }
    try {
      var r = await fetch('/api/maquila/clientes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
      var d = await r.json();
      if(!r.ok){ alert('Error: '+(d.error||'')); return; }
      document.getElementById('modal-mq-cliente').style.display='none';
      _toast('✓ Cliente creado', 1);
      cargarClientesMaquila();
    } catch(e){ alert('Error: '+e.message); }
  }

  async function cancelarPedidoMaquila(id){
    if(!confirm('¿Cancelar este pedido de maquila?')) return;
    try {
      var r = await fetch('/api/maquila/pedidos/'+id, {method:'DELETE'});
      if(r.ok){ _toast('Pedido cancelado', 1); cargarPedidosMaquila(); }
    } catch(e){ alert('Error: '+e.message); }
  }

  function editarLoteModal(prodId, producto, kgActual){
    var nueva = prompt('Editar tamaño del lote para "'+producto+'"\\n\\nKg actuales: '+kgActual+'\\n\\nNuevo tamaño (kg):', kgActual);
    if(nueva === null) return;
    nueva = parseFloat(nueva);
    if(isNaN(nueva) || nueva <= 0){ alert('Cantidad inválida'); return; }
    fetch('/api/planta/produccion/'+prodId+'/editar-lote', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cantidad_kg: nueva})
    }).then(function(r){return r.json();}).then(function(d){
      if(!d.ok){ alert('Error: '+(d.error||'')); return; }
      var msg = '✓ Lote actualizado a '+nueva+'kg';
      if(d.envase_recalculado){
        msg += '\\nEnvases ahora: '+d.envase_recalculado.unidades_requeridas+' unidades';
      }
      if(d.mp_recalculada && d.mp_recalculada.length){
        var top3 = d.mp_recalculada.slice(0,3).map(function(m){return m.material_nombre+': '+m.gramos_requeridos+'g'}).join('\\n');
        msg += '\\n\\nMP recalculada:\\n'+top3;
      }
      alert(msg);
      planV2Cargar();
    });
  }

  function planV2RenderSemana(d){
    var kpis = document.getElementById('pv2-kpis');
    var k = d.kpis || {};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Producciones 14d</div><div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.alerta_roja_dias?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Alerta días &lt;10</div><div style="font-size:26px;font-weight:800;color:'+(k.alerta_roja_dias?'#dc2626':'#15803d')+'">'+(k.alerta_roja_dias||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.sin_mp_suficiente?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Sin MP</div><div style="font-size:26px;font-weight:800;color:'+(k.sin_mp_suficiente?'#dc2626':'#15803d')+'">'+(k.sin_mp_suficiente||0)+'</div></div>';

    document.getElementById('pv2-comprar-ya').style.display = 'none';

    var vista = document.getElementById('pv2-vista');
    var items = d.items || [];
    if(!items.length){
      vista.innerHTML = '<div style="background:#f0fdf4;padding:30px;border-radius:10px;text-align:center;color:#166534;font-size:14px">✓ Sin producciones próximas — todo dentro de cobertura</div>';
      return;
    }
    vista.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px">'
      + items.map(function(it){
        var diasCol = it.alerta_dias==='rojo'?'#dc2626':(it.alerta_dias==='amarillo'?'#d97706':(it.alerta_dias==='verde'?'#15803d':'#94a3b8'));
        var diasTxt = it.dias_inventario===null?'—':it.dias_inventario+'d';
        var mpCol = it.alcanza_mp?'#15803d':'#dc2626';
        var img = it.imagen_url
          ? '<img src="'+_escAttr(it.imagen_url)+'" style="width:100%;height:110px;object-fit:cover" alt="">'
          : '<div style="width:100%;height:110px;background:linear-gradient(135deg,#0f766e,#0891b2);display:flex;align-items:center;justify-content:center;color:#fff;font-size:32px">📦</div>';
        return '<div onclick="abrirPlanSemModal('+it.produccion_id+')" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;cursor:pointer;transition:transform .12s">'
          + img
          +'<div style="padding:10px 12px"><b style="color:#0f172a;font-size:13px">'+_escHTML(it.producto)+'</b>'
          +'<div style="font-size:11px;color:#64748b;margin-top:2px">📅 '+_escHTML(it.fecha_programada)+' · '+(it.lotes||1)+' lote(s)</div>'
          +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:8px">'
          +'<div style="background:'+diasCol+'15;color:'+diasCol+';padding:5px;border-radius:5px;text-align:center;font-size:10px;font-weight:700">⏰ '+diasTxt+'</div>'
          +'<div style="background:'+mpCol+'15;color:'+mpCol+';padding:5px;border-radius:5px;text-align:center;font-size:10px;font-weight:700">'+(it.alcanza_mp?'✓ MP':'✗ MP')+'</div>'
          +'</div></div></div>';
      }).join('')
      +'</div>';
  }

  function planV2RenderForecast(d, meses){
    var k = d.kpis || {};
    var kpis = document.getElementById('pv2-kpis');
    var desglose = k.desglose || {};
    var dMotor = desglose.motor_mrp || {lotes:0,kg:0,skus:0};
    var dBd = desglose.bd_interna || {lotes:0,kg:0,skus:0};
    var dCal = desglose.google_calendar || {lotes:0,kg:0,skus:0};
    kpis.innerHTML = ''
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:14px">'
        +'<div style="font-size:11px;color:#64748b;text-transform:uppercase">Total lotes planeados</div>'
        +'<div style="font-size:26px;font-weight:800;color:#0f172a">'+(k.total_lotes_proyectados||0)+'</div>'
        +'<div style="font-size:10px;color:#64748b;margin-top:4px">📆 '+dCal.lotes+' Calendar · 🤖 '+dMotor.lotes+' Motor · ✓ '+dBd.lotes+' BD</div>'
      +'</div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Total kg</div><div style="font-size:26px;font-weight:800;color:#15803d">'+(k.total_kg_proyectados||0).toLocaleString('es-CO')+'</div><div style="font-size:10px;color:#64748b;margin-top:4px">📆 '+dCal.kg+'kg · 🤖 '+dMotor.kg+'kg</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">SKUs distintos</div><div style="font-size:26px;font-weight:800;color:#7c3aed">'+(k.productos_distintos||0)+'</div><div style="font-size:10px;color:#64748b;margin-top:4px">con producción en horizonte</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.compras_urgentes_count?'#dc2626':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">🛒 Comprar YA</div><div style="font-size:26px;font-weight:800;color:'+(k.compras_urgentes_count?'#dc2626':'#15803d')+'">'+(k.compras_urgentes_count||0)+'</div></div>'
      +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(k.meses_con_alerta_capacidad?'#d97706':'#15803d')+';border-radius:10px;padding:14px"><div style="font-size:11px;color:#64748b;text-transform:uppercase">Meses cuello botella</div><div style="font-size:26px;font-weight:800;color:'+(k.meses_con_alerta_capacidad?'#d97706':'#15803d')+'">'+(k.meses_con_alerta_capacidad||0)+'</div></div>';

    // Sección comprar YA (urgentes)
    var compYa = d.compras_urgentes || [];
    var box = document.getElementById('pv2-comprar-ya');
    if(compYa.length){
      box.style.display = 'block';
      box.innerHTML = '<div style="background:#fef2f2;border:2px solid #dc2626;border-radius:12px;padding:16px">'
        +'<h3 style="margin:0 0 10px;color:#991b1b">🚨 Comprar AHORA · '+compYa.length+' material(es) por lead time</h3>'
        +'<div style="font-size:12px;color:#7f1d1d;margin-bottom:10px">Estos envases NO llegarán a tiempo si no se piden hoy. Lead time China = 180 días.</div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px"><thead><tr style="background:#fee2e2"><th style="padding:8px;text-align:left">Envase</th><th style="padding:8px;text-align:right">Cantidad</th><th style="padding:8px;text-align:left">Origen</th><th style="padding:8px;text-align:right">Lead</th><th style="padding:8px;text-align:right">Necesario para</th></tr></thead><tbody>'
        + compYa.map(function(c){
          return '<tr style="border-top:1px solid #fecaca">'
            +'<td style="padding:6px 8px"><b>'+_escHTML(c.etiqueta)+'</b><br><code style="font-size:10px;color:#991b1b">'+_escHTML(c.envase_codigo)+'</code></td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:800">'+c.unidades_requeridas.toLocaleString('es-CO')+'</td>'
            +'<td style="padding:6px 8px"><span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+_escHTML(c.origen)+'</span></td>'
            +'<td style="padding:6px 8px;text-align:right;font-family:monospace">'+c.lead_time_dias+'d</td>'
            +'<td style="padding:6px 8px;text-align:right">'+_escHTML(c.mes_objetivo)+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } else {
      box.style.display = 'none';
    }

    var vista = document.getElementById('pv2-vista');
    if(meses === 1){
      planV2RenderCalendarioMes(d, vista);
    } else if(meses <= 3){
      planV2RenderTimeline(d, vista, meses);
    } else {
      planV2RenderHeatmap(d, vista, meses);
    }
  }

  async function planV2RenderCalendarioMes(d, vista){
    // Agrupar producciones del MOTOR por fecha
    var prods = d.producciones_proyectadas || [];
    var porFecha = {};
    prods.forEach(function(p){
      porFecha[p.fecha] = porFecha[p.fecha] || [];
      porFecha[p.fecha].push({producto: p.producto, origen: 'motor', kg: p.kg_con_merma});
    });

    // Sumar eventos REALES del Google Calendar
    try {
      var rcal = await fetch('/api/planta/calendar-eventos-plan?dias=35');
      var dcal = await rcal.json();
      (dcal.eventos || []).forEach(function(ev){
        porFecha[ev.fecha] = porFecha[ev.fecha] || [];
        porFecha[ev.fecha].push({
          producto: ev.producto_match || ev.titulo,
          titulo_real: ev.titulo,
          origen: 'calendar',
          kg: ev.kg,
          score: ev.score,
        });
      });
    } catch(e){ /* silent */ }

    var hoy = new Date(d.fecha_inicio);
    var html = '<h3 style="margin:0 0 8px;color:#0f172a;font-size:15px">📅 Calendario próximos 30 días</h3>';
    html += '<div style="display:flex;gap:14px;font-size:11px;color:#64748b;margin-bottom:8px;flex-wrap:wrap">'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#0891b2;border-radius:2px;vertical-align:middle"></span> Google Calendar (real)</span>'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#7c3aed;border-radius:2px;vertical-align:middle"></span> Motor MRP (proyectado)</span>'
      +'<span><span style="display:inline-block;width:10px;height:10px;background:#15803d;border-radius:2px;vertical-align:middle"></span> Confirmado en BD</span>'
      +'</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;font-size:11px">';
    ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'].forEach(function(dn){
      html += '<div style="font-weight:800;color:#475569;text-align:center;padding:6px;background:#f1f5f9;border-radius:4px">'+dn+'</div>';
    });
    var pad = (hoy.getDay() + 6) % 7;
    for(var i=0;i<pad;i++) html += '<div></div>';
    for(var d_=0; d_<30; d_++){
      var fecha = new Date(hoy); fecha.setDate(fecha.getDate()+d_);
      var fStr = fecha.toISOString().substring(0,10);
      var weekday = (fecha.getDay()+6)%7;
      var esLMV = [0,2,4].indexOf(weekday) >= 0;
      var prodsDia = porFecha[fStr] || [];
      var bg = esLMV ? '#fff' : '#f9fafb';
      var border = prodsDia.length ? '#0f766e' : '#e5e7eb';
      html += '<div style="background:'+bg+';border:1px solid '+border+';border-radius:6px;padding:6px;min-height:70px;font-size:10px">'
        +'<div style="color:#94a3b8;font-weight:700;font-size:10px">'+fecha.getDate()+'</div>'
        + prodsDia.slice(0,4).map(function(p){
          var col = p.origen==='calendar' ? '#0891b2' : '#7c3aed';
          var bgCol = p.origen==='calendar' ? '#cffafe' : '#ede9fe';
          var txtCol = p.origen==='calendar' ? '#155e75' : '#5b21b6';
          var label = p.titulo_real || p.producto;
          var kgTxt = p.kg ? ' '+Math.round(p.kg)+'kg' : '';
          return '<div style="background:'+bgCol+';color:'+txtCol+';padding:2px 4px;border-radius:3px;margin-top:2px;font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-left:2px solid '+col+'" title="'+_escAttr((p.titulo_real||p.producto)+kgTxt+' · '+p.origen)+'">'+_escHTML(label.substring(0,16))+kgTxt+'</div>';
        }).join('')
        + (prodsDia.length>4?'<div style="font-size:9px;color:#64748b;margin-top:2px">+'+(prodsDia.length-4)+' más</div>':'')
        +'</div>';
    }
    html += '</div>';
    vista.innerHTML = html;
  }

  function planV2RenderTimeline(d, vista, meses){
    // Agrupar producciones por SKU
    var prods = d.producciones_proyectadas || [];
    var porSku = {};
    prods.forEach(function(p){ porSku[p.producto] = porSku[p.producto] || []; porSku[p.producto].push(p); });
    var hoy = new Date(d.fecha_inicio);
    var fin = new Date(d.fecha_fin);
    var dias = Math.round((fin - hoy) / (1000*60*60*24));

    var html = '<h3 style="margin:0 0 10px;color:#0f172a;font-size:15px">📊 Timeline · '+meses+' meses</h3>';
    html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;overflow-x:auto">';
    // Eje X: meses
    html += '<div style="display:grid;grid-template-columns:200px 1fr;gap:10px;border-bottom:1px solid #e5e7eb;padding-bottom:6px;margin-bottom:8px;font-size:11px;font-weight:700;color:#64748b">';
    html += '<div>SKU</div>';
    html += '<div style="display:grid;grid-template-columns:repeat('+meses+',1fr)">';
    for(var m=0;m<meses;m++){
      var d2 = new Date(hoy); d2.setMonth(d2.getMonth()+m);
      html += '<div style="text-align:center">'+d2.toLocaleString('es-CO',{month:'short',year:'2-digit'}).toUpperCase()+'</div>';
    }
    html += '</div></div>';
    // Filas SKU
    Object.keys(porSku).sort().forEach(function(sku){
      html += '<div style="display:grid;grid-template-columns:200px 1fr;gap:10px;align-items:center;padding:5px 0;border-top:1px solid #f1f5f9;font-size:11px">';
      html += '<div style="font-weight:600;color:#0f172a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escAttr(sku)+'">'+_escHTML(sku)+'</div>';
      html += '<div style="position:relative;height:20px;background:#f8fafc;border-radius:3px">';
      porSku[sku].forEach(function(p){
        var pf = new Date(p.fecha);
        var offset = (pf - hoy) / (fin - hoy) * 100;
        if(offset < 0 || offset > 100) return;
        html += '<div title="'+_escAttr(p.fecha+' · '+p.kg_con_merma+'kg')+'" style="position:absolute;left:'+offset+'%;top:2px;width:8px;height:16px;background:#0f766e;border-radius:2px"></div>';
      });
      html += '</div></div>';
    });
    html += '</div>';

    // Tabla resumen mensual
    html += '<h3 style="margin:18px 0 10px;color:#0f172a;font-size:15px">📈 Resumen mensual</h3>';
    html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">';
    html += '<thead style="background:#f9fafb"><tr><th style="padding:8px 12px;text-align:left">Mes</th><th style="padding:8px;text-align:right">Lotes</th><th style="padding:8px;text-align:right">Kg total</th><th style="padding:8px;text-align:right">SKUs</th></tr></thead><tbody>';
    var resumen = d.resumen_mensual || {};
    Object.keys(resumen).sort().forEach(function(m){
      var r = resumen[m];
      html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:7px 12px;font-weight:700">'+_escHTML(m)+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.lotes+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.kg_total+'</td><td style="padding:7px;text-align:right;font-family:monospace">'+r.productos_distintos+'</td></tr>';
    });
    html += '</tbody></table></div>';

    vista.innerHTML = html;
  }

  function planV2RenderHeatmap(d, vista, meses){
    // Heatmap SKU × mes (intensidad = kg)
    var prods = d.producciones_proyectadas || [];
    var skus = [...new Set(prods.map(function(p){return p.producto}))].sort();
    var meses_keys = Object.keys(d.resumen_mensual || {}).sort();

    // Calcular max kg por celda para normalizar color
    var celda = {};
    prods.forEach(function(p){
      var k = p.producto+'|'+p.mes;
      celda[k] = (celda[k]||0) + p.kg_con_merma;
    });
    var maxVal = Math.max(...Object.values(celda), 1);

    var html = '<h3 style="margin:0 0 10px;color:#0f172a;font-size:15px">🌡 Mapa de calor · '+meses+' meses</h3>';
    html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px;overflow-x:auto">';
    html += '<div style="display:grid;grid-template-columns:240px repeat('+meses_keys.length+',minmax(50px,1fr));gap:2px;font-size:10px">';
    html += '<div></div>';
    meses_keys.forEach(function(m){
      html += '<div style="text-align:center;padding:6px 4px;background:#f1f5f9;border-radius:3px;font-weight:700;color:#475569">'+_escHTML(m.substring(5))+'</div>';
    });
    skus.forEach(function(sku){
      html += '<div style="padding:6px 8px;font-size:11px;font-weight:600;color:#0f172a;background:#f8fafc;border-radius:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_escAttr(sku)+'">'+_escHTML(sku.substring(0,30))+'</div>';
      meses_keys.forEach(function(m){
        var v = celda[sku+'|'+m] || 0;
        var pct = Math.min(100, (v/maxVal)*100);
        var bg = v > 0 ? 'rgba(15,118,110,'+(0.15+pct/130)+')' : '#fafafa';
        html += '<div style="padding:6px 4px;background:'+bg+';border-radius:3px;text-align:center;font-size:10px;color:'+(v>maxVal*0.5?'#fff':'#0f172a')+';font-weight:700" title="'+_escAttr(sku+' · '+m+': '+v.toFixed(0)+'kg')+'">'+(v>0?v.toFixed(0):'')+'</div>';
      });
    });
    html += '</div></div>';

    // Necesidades agregadas año
    if(meses >= 6){
      html += '<h3 style="margin:18px 0 10px;color:#0f172a;font-size:15px">🛒 Necesidades agregadas '+meses+' meses</h3>';
      // Sumar MP total
      var mpTotal = {};
      Object.values(d.mp_consumo_mensual || {}).forEach(function(mes){
        Object.keys(mes).forEach(function(matId){
          mpTotal[matId] = mpTotal[matId] || {nombre: mes[matId].nombre, gramos: 0};
          mpTotal[matId].gramos += mes[matId].gramos;
        });
      });
      var mpArr = Object.entries(mpTotal).map(function(e){return Object.assign({material_id:e[0]}, e[1]);}).sort(function(a,b){return b.gramos-a.gramos;}).slice(0,15);
      html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;margin-bottom:14px">';
      html += '<div style="padding:10px 14px;background:#f9fafb;font-weight:700;font-size:12px;color:#475569">Top 15 materias primas</div>';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr><th style="padding:6px 10px;text-align:left">Material</th><th style="padding:6px 10px;text-align:right">Total gramos</th><th style="padding:6px 10px;text-align:right">Total kg</th></tr></thead><tbody>';
      mpArr.forEach(function(m){
        html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:6px 10px"><b>'+_escHTML(m.nombre||m.material_id)+'</b></td><td style="padding:6px 10px;text-align:right;font-family:monospace">'+Math.round(m.gramos).toLocaleString('es-CO')+'</td><td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:700">'+(m.gramos/1000).toFixed(2)+'</td></tr>';
      });
      html += '</tbody></table></div>';

      // Envases agregados
      var envTotal = {};
      Object.values(d.envases_consumo_mensual || {}).forEach(function(mes){
        Object.keys(mes).forEach(function(cod){
          envTotal[cod] = envTotal[cod] || {etiqueta: mes[cod].etiqueta, unidades: 0};
          envTotal[cod].unidades += mes[cod].unidades;
        });
      });
      var envArr = Object.entries(envTotal).map(function(e){return Object.assign({codigo:e[0]}, e[1]);}).sort(function(a,b){return b.unidades-a.unidades;});
      if(envArr.length){
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">';
        html += '<div style="padding:10px 14px;background:#f9fafb;font-weight:700;font-size:12px;color:#475569">Envases requeridos</div>';
        html += '<table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr><th style="padding:6px 10px;text-align:left">Envase</th><th style="padding:6px 10px;text-align:right">Unidades</th></tr></thead><tbody>';
        envArr.forEach(function(e){
          html += '<tr style="border-top:1px solid #f1f5f9"><td style="padding:6px 10px"><b>'+_escHTML(e.etiqueta)+'</b> <code style="font-size:10px;color:#64748b">'+_escHTML(e.codigo)+'</code></td><td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:700">'+e.unidades.toLocaleString('es-CO')+'</td></tr>';
        });
        html += '</tbody></table></div>';
      }
    }
    vista.innerHTML = html;
  }

  // ════════════════════════════════════════════════════════════════════════
  // ASIGNACIÓN SEMANAL · qué hace cada área cada día
  // ════════════════════════════════════════════════════════════════════════
  var _ASIG_FECHA = null;
  function asigInit(){
    var hoy = new Date();
    document.getElementById('asig-fecha').value = hoy.toISOString().substring(0,10);
    _ASIG_FECHA = hoy;
    asigCargar();
  }
  function asigSemana(delta){
    var input = document.getElementById('asig-fecha');
    var f = input.value ? new Date(input.value) : new Date();
    if(delta === 0) f = new Date();
    else f.setDate(f.getDate() + delta*7);
    input.value = f.toISOString().substring(0,10);
    asigCargar();
  }
  async function asigCargar(){
    var grid = document.getElementById('asig-grid');
    var fecha = document.getElementById('asig-fecha').value;
    grid.innerHTML = '<div style="text-align:center;padding:40px;color:#94a3b8">Cargando...</div>';
    try {
      var r = await fetch('/api/planta/asignacion-semanal?fecha='+fecha);
      var d = await r.json();
      var dias = d.dias || [];
      var areas = d.areas || [];
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">';
      html += '<table style="width:100%;border-collapse:collapse;font-size:12px;min-width:900px">';
      // Header
      html += '<thead><tr style="background:#1f2937;color:#fff">';
      html += '<th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.5px">Área</th>';
      dias.forEach(function(dia){
        var bg = dia.es_lmv ? '#0f766e' : '#475569';
        var ico = dia.es_lmv ? '⚙️' : '📦';
        html += '<th style="padding:10px 8px;text-align:center;font-size:11px;background:'+bg+';text-transform:uppercase;letter-spacing:.3px">'+ico+' '+_escHTML(dia.nombre)+'<br><span style="font-weight:400;font-size:9px;opacity:.85">'+_escHTML(dia.fecha.substring(5))+'</span></th>';
      });
      html += '</tr></thead><tbody>';
      areas.forEach(function(area){
        if(!area.puede_producir && !area.puede_envasar && area.tipo!=='apoyo_asignable') return;
        html += '<tr style="border-top:1px solid #e2e8f0">';
        var areaCol = area.requiere_limpieza_profunda ? '#0891b2' : '#94a3b8';
        html += '<td style="padding:10px 12px;background:#f8fafc"><b style="color:#0f172a">'+_escHTML(area.nombre)+'</b><br><code style="color:'+areaCol+';font-size:10px">'+_escHTML(area.codigo)+'</code>'+(area.requiere_limpieza_profunda?'<br><span style="font-size:9px;color:#0891b2;font-weight:700">🧹 LIMP. PROF.</span>':'')+'</td>';
        ['lunes','martes','miercoles','jueves','viernes'].forEach(function(nd){
          var datos = area.dias[nd] || {};
          var prods = datos.producciones || [];
          var limps = datos.limpiezas || [];
          var conts = datos.conteos || [];
          var celda = '';
          prods.forEach(function(p){
            celda += '<div style="background:#dbeafe;color:#1e40af;padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px"><b>🔬 '+_escHTML(p.producto.substring(0,22))+'</b>'+(p.lotes>1?' ×'+p.lotes:'')+(p.op_elaboracion?'<br>👤 '+_escHTML(p.op_elaboracion.substring(0,20)):'')+'</div>';
          });
          limps.forEach(function(l){
            celda += '<div style="background:#fef3c7;color:#92400e;padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px;font-weight:700">🧹 Limpieza profunda<br><span style="font-weight:400">'+_escHTML(l.asignado_a||'—')+'</span></div>';
          });
          conts.forEach(function(c){
            celda += '<div style="background:#f3e8ff;color:#6b21a8;padding:4px 6px;border-radius:4px;margin-bottom:3px;font-size:10px">📦 '+_escHTML((c.material||'').substring(0,18))+'</div>';
          });
          if(!celda) celda = '<div style="color:#cbd5e1;text-align:center;font-size:11px;padding:8px">—</div>';
          html += '<td style="padding:6px;vertical-align:top;background:'+(datos.es_dia_produccion?'#fff':'#fafafa')+'">'+celda+'</td>';
        });
        html += '</tr>';
      });
      html += '</tbody></table></div>';

      // Tareas globales (sin área)
      var tareasG = d.tareas_globales || [];
      if(tareasG.length){
        html += '<h3 style="margin:18px 0 10px;color:#0f172a;font-size:14px">📋 Tareas operativas (sin área específica)</h3>';
        html += '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:12px;font-size:12px">';
        tareasG.forEach(function(t){
          html += '<div style="padding:6px 0;border-bottom:1px solid #f1f5f9"><b>'+_escHTML(t.fecha)+'</b> · '+_escHTML(t.titulo)+' · '+_escHTML(t.asignado_a||'')+'</div>';
        });
        html += '</div>';
      }

      grid.innerHTML = html;
    } catch(e){
      grid.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  // ════════════════════════════════════════════════════════════════════════
  // CONFIGURACIÓN · sub-tabs (Presentaciones, Equipos, Cadencias, etc.)
  // ════════════════════════════════════════════════════════════════════════
  var _CFG_SUB = 'pres';
  function cfgInit(){ cfgSubtab(_CFG_SUB); }
  function cfgSubtab(s){
    _CFG_SUB = s;
    ['pres','equipos','cadencias','mp','emails','riesgo','calendar'].forEach(function(x){
      var btn = document.getElementById('cfg-stab-'+x);
      if(btn){
        if(x==='calendar'){
          btn.style.background = (s===x)?'#dc2626':'linear-gradient(135deg,#fbbf24,#dc2626)';
          btn.style.color = '#fff';
        } else {
          btn.style.background = (s===x)?'#1f2937':'#e5e7eb';
          btn.style.color = (s===x)?'#fff':'#475569';
        }
      }
    });
    var c = document.getElementById('cfg-content');
    // Cargamos los divs antiguos como contenido — reusamos sus cargadores
    if(s==='pres'){
      c.innerHTML = '<div id="ptab-presentaciones-host"></div>';
      // Mover el contenido de ptab-presentaciones aquí (clonando)
      var src = document.getElementById('ptab-presentaciones');
      if(src) c.innerHTML = src.outerHTML.replace('display:none','display:block').replace('id="ptab-presentaciones"','id="ptab-presentaciones-rendered"');
      if(typeof cargarPresentaciones==='function') setTimeout(cargarPresentaciones, 50);
    } else if(s==='equipos'){
      var src = document.getElementById('ptab-equipos');
      if(src) c.innerHTML = src.outerHTML.replace('display:none','display:block').replace('id="ptab-equipos"','id="ptab-equipos-rendered"');
      if(typeof cargarEquipos==='function') setTimeout(cargarEquipos, 50);
    } else if(s==='cadencias'){
      c.innerHTML = '<p style="color:#64748b;font-size:13px">Cadencia, cobertura y merma por SKU. Edita inline.</p><div id="ap-skus-tabla"></div>';
      if(typeof apCargarSkus==='function') setTimeout(apCargarSkus, 50);
    } else if(s==='mp'){
      c.innerHTML = '<div style="display:flex;justify-content:flex-end;margin-bottom:10px"><button onclick="apMpNuevo()" style="background:#0f766e;color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">+ Nuevo material</button></div><div id="ap-mp-tabla"></div>';
      if(typeof apCargarMp==='function') setTimeout(apCargarMp, 50);
    } else if(s==='emails'){
      c.innerHTML = '<div id="ap-emails-tabla"></div>';
      if(typeof apCargarEmails==='function') setTimeout(apCargarEmails, 50);
    } else if(s==='riesgo'){
      c.innerHTML = '<p style="color:#64748b;font-size:13px">Productos con perfil de riesgo (pigmento, ácido, sensibilidad). Usado por el motor de gates pre-flight para detectar arrastre crítico.</p><div id="cfg-riesgo-tabla"><div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div></div>';
      cfgCargarRiesgo();
    } else if(s==='calendar'){
      c.innerHTML = '<div style="background:linear-gradient(135deg,#fef3c7,#fbbf24);color:#78350f;padding:14px 18px;border-radius:10px;margin-bottom:14px">'
        +'<h3 style="margin:0 0 4px;color:#78350f;font-size:15px">📆 Lectura del Google Calendar</h3>'
        +'<p style="margin:0;font-size:12px;color:#7c2d12">El motor MRP lee tu calendario y matchea cada evento con un producto. Revisa que estén bien matcheados — si hay errores, configura aliases en la sección de cadencias.</p>'
        +'</div>'
        +'<div style="display:flex;gap:8px;margin-bottom:12px"><button onclick="cfgCargarCalendar()" style="background:#dc2626;color:#fff;border:none;padding:8px 14px;border-radius:6px;font-weight:700;cursor:pointer">🔄 Re-leer Calendar</button><button onclick="cfgCargarAliases()" style="background:#fff;border:1px solid #cbd5e1;padding:8px 14px;border-radius:6px;font-weight:600;cursor:pointer">⚙ Editar aliases</button></div>'
        +'<div id="cfg-cal-kpis" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:14px"></div>'
        +'<div id="cfg-cal-tabla"><div style="text-align:center;color:#94a3b8;padding:20px">Pulsa "Re-leer Calendar"</div></div>';
      cfgCargarCalendar();
    }
  }

  async function cfgCargarCalendar(){
    var box = document.getElementById('cfg-cal-tabla');
    var kpis = document.getElementById('cfg-cal-kpis');
    if(!box) return;
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Leyendo calendar...</div>';
    try {
      var r = await fetch('/api/planta/calendar-debug');
      var d = await r.json();
      if(!r.ok){ box.innerHTML = '<div style="color:#dc2626">Error: '+(d.error||'')+'</div>'; return; }
      kpis.innerHTML = ''
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0891b2;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">Eventos</div><div style="font-size:24px;font-weight:800;color:#0f172a">'+d.total_eventos+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #15803d;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">✓ Matcheados</div><div style="font-size:24px;font-weight:800;color:#15803d">'+d.matcheados+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(d.en_conflicto?'#dc2626':'#15803d')+';border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">⚠ Conflicto</div><div style="font-size:24px;font-weight:800;color:'+(d.en_conflicto?'#dc2626':'#15803d')+'">'+d.en_conflicto+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid '+(d.sin_match_aceptable?'#d97706':'#15803d')+';border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">? Sin match</div><div style="font-size:24px;font-weight:800;color:'+(d.sin_match_aceptable?'#d97706':'#15803d')+'">'+d.sin_match_aceptable+'</div></div>'
        +'<div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:10px;padding:12px"><div style="font-size:10px;color:#64748b;text-transform:uppercase">⚖ Con kg</div><div style="font-size:24px;font-weight:800;color:#7c3aed">'+d.con_kg_detectados+'</div></div>';
      var eventos = d.eventos || [];
      if(!eventos.length){
        box.innerHTML = '<div style="background:#fef3c7;border:1px solid #fbbf24;color:#92400e;padding:20px;border-radius:10px;text-align:center"><b>Sin eventos en calendar</b><br><span style="font-size:12px">Verifica que GCAL_ICAL_URL esté configurado en Render.</span></div>';
        return;
      }
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Evento</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Fecha</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Kg</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto matcheado</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Score</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Estado</th>'
        +'</tr></thead><tbody>';
      eventos.forEach(function(e){
        var col = {matcheado:'#15803d',conflicto:'#dc2626',sin_match:'#d97706',no_relacionado:'#94a3b8'}[e.estado] || '#475569';
        var ico = {matcheado:'✓',conflicto:'⚠',sin_match:'?',no_relacionado:'·'}[e.estado] || '';
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px"><b>'+_escHTML(e.titulo)+'</b></td>'
          +'<td style="padding:7px 10px;font-family:monospace;font-size:11px">'+_escHTML(e.fecha)+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;font-weight:700">'+(e.kg_detectados!=null?e.kg_detectados+'kg':'<span style="color:#94a3b8">—</span>')+'</td>'
          +'<td style="padding:7px 10px;font-size:11px">'+(e.producto_match?'<b>'+_escHTML(e.producto_match)+'</b>':'<span style="color:#94a3b8">—</span>')+'</td>'
          +'<td style="padding:7px 10px;text-align:right;font-family:monospace;color:'+col+';font-weight:700">'+e.score_match+'</td>'
          +'<td style="padding:7px 10px;text-align:center"><span style="background:'+col+'22;color:'+col+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+ico+' '+e.estado+'</span></td>'
          +'</tr>';
        if(e.candidatos_top3 && e.candidatos_top3.length > 1 && e.estado==='conflicto'){
          html += '<tr><td colspan="6" style="padding:4px 30px;background:#fef2f2;font-size:10px;color:#7f1d1d">Candidatos: '+e.candidatos_top3.map(function(cc){return cc.producto+' ('+cc.score+')'}).join(' · ')+'</td></tr>';
        }
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    } catch(err){ box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+err.message+'</div>'; }
  }

  async function cfgCargarAliases(){
    var box = document.getElementById('cfg-cal-tabla');
    box.innerHTML = '<div style="text-align:center;color:#94a3b8;padding:20px">Cargando...</div>';
    try {
      var r = await fetch('/api/auto-plan/configs/sku');
      var d = await r.json();
      var rows = d.configs || [];
      var html = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow-x:auto">'
        +'<div style="padding:12px 14px;background:#f9fafb;font-size:12px;color:#475569"><b>Aliases del Calendar por producto</b><br><span style="font-size:11px;color:#64748b">Separa con coma. Ejemplo: <code style="background:#fff;padding:1px 5px;border-radius:3px">AH 1.5%, AH, Hidratante AH</code></span></div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px">'
        +'<thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Aliases (CSV)</th>'
        +'</tr></thead><tbody>';
      rows.forEach(function(c){
        html += '<tr style="border-top:1px solid #f1f5f9">'
          +'<td style="padding:7px 10px"><b>'+_escHTML(c.producto_nombre)+'</b></td>'
          +'<td style="padding:5px 10px"><input type="text" value="'+_escAttr(c.alias_calendar||'')+'" placeholder="alias1, alias2, ..." onblur="apAliasGuardar('+c.id+', this)" style="width:100%;padding:6px 8px;border:1px solid #cbd5e1;border-radius:5px;font-size:12px"></td>'
          +'</tr>';
      });
      html += '</tbody></table></div>';
      box.innerHTML = html;
    } catch(e){ box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>'; }
  }

  async function apAliasGuardar(id, input){
    try {
      var r = await fetch('/api/auto-plan/configs/sku/'+id, {
        method:'PUT', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({alias_calendar: input.value.trim() || null})
      });
      if(r.ok){ input.style.background='#f0fdf4'; setTimeout(function(){input.style.background='';}, 800); }
    } catch(e){}
  }

  async function cfgCargarRiesgo(){
    var box = document.getElementById('cfg-riesgo-tabla');
    if(!box) return;
    try {
      var r = await fetch('/api/auto-plan/configs/perfil-riesgo');
      var d = await r.json();
      var rows = d.perfiles || [];
      box.innerHTML = '<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden"><table style="width:100%;border-collapse:collapse;font-size:12px"><thead style="background:#f9fafb"><tr>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Producto</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Pigmento</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Color</th>'
        +'<th style="padding:8px 10px;text-align:center;font-size:10px;color:#475569;text-transform:uppercase">Ácido</th>'
        +'<th style="padding:8px 10px;text-align:right;font-size:10px;color:#475569;text-transform:uppercase">Riesgo arrastre</th>'
        +'<th style="padding:8px 10px;text-align:left;font-size:10px;color:#475569;text-transform:uppercase">Notas</th>'
        +'</tr></thead><tbody>'
        + rows.map(function(p){
          var pigCol = p.tiene_pigmento ? '#dc2626' : '#94a3b8';
          var rieCol = p.riesgo_arrastre_pct >= 50 ? '#dc2626' : (p.riesgo_arrastre_pct >= 25 ? '#d97706' : '#15803d');
          return '<tr style="border-top:1px solid #f1f5f9">'
            +'<td style="padding:7px 10px"><b>'+_escHTML(p.producto_nombre)+'</b></td>'
            +'<td style="padding:7px 10px;text-align:center"><span style="background:'+pigCol+'22;color:'+pigCol+';padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700">'+(p.tiene_pigmento?'SÍ':'no')+'</span></td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML(p.color_descripcion||'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:center">'+(p.es_acido?'🧪':'—')+'</td>'
            +'<td style="padding:7px 10px;text-align:right;color:'+rieCol+';font-weight:700">'+p.riesgo_arrastre_pct+'%</td>'
            +'<td style="padding:7px 10px;font-size:11px;color:#64748b">'+_escHTML((p.notas||'').substring(0,60))+'</td>'
            +'</tr>';
        }).join('')
        +'</tbody></table></div>';
    } catch(e){
      box.innerHTML = '<div style="color:#dc2626;padding:14px">Error: '+e.message+'</div>';
    }
  }

  // Safe modal backdrop close — placed after all functions are defined
  (function(){
    var _m = document.getElementById('modal-programar');
    if(_m) _m.addEventListener('click', function(e){ if(e.target===this) cerrarModalProgramar(); });
  })();

  var _planLoaded = false;
  var _planData   = null;
  var _planDias   = 60;

  function _setPlanHorizonBtn(d){
    [15,30,60,90,180,365].forEach(function(n){
      var b=document.getElementById('plan-btn-'+n);
      if(b){ b.style.background=d===n?'#1a4a7a':'#fff'; b.style.color=d===n?'#fff':'#1a4a7a'; }
    });
  }

  async function cargarPlanificacion(dias){
    _planDias=dias;
    _setPlanHorizonBtn(dias);
    document.getElementById('plan-empty').style.display='none';
    document.getElementById('plan-loading').style.display='block';
    document.getElementById('plan-error').style.display='none';
    document.getElementById('plan-cards').innerHTML='';
    document.getElementById('plan-deficit-box').style.display='none';
    document.getElementById('plan-ok-box').style.display='none';
    document.getElementById('plan-bulk-box').style.display='none';
    document.getElementById('plan-prods-box').style.display='none';
    var staffBox=document.getElementById('plan-staff-box'); if(staffBox) staffBox.style.display='none';
    var prodsDetailBox=document.getElementById('plan-prods-detail-box'); if(prodsDetailBox) prodsDetailBox.style.display='none';
    try{
      var r=await fetch('/api/programacion/planificacion?dias='+dias);
      var d=await r.json();
      document.getElementById('plan-loading').style.display='none';
      if(d.cal_error){
        document.getElementById('plan-error').style.display='block';
        document.getElementById('plan-error').innerHTML='&#9888; Calendario: '+d.cal_error;
      }
      _planData=d;
      _planLoaded=true;
      _renderPlanificacion(d);
    }catch(e){
      document.getElementById('plan-loading').style.display='none';
      var errDiv = document.getElementById('plan-error');
      errDiv.style.display='block';
      errDiv.style.background='#f8d7da';
      errDiv.style.border='2px solid #dc3545';
      errDiv.style.padding='16px';
      errDiv.style.fontSize='14px';
      errDiv.innerHTML='<strong>⚠ Error al cargar planificacion:</strong><br>' + e.message + '<br><small>' + (e.stack||'') + '</small>';
      _toast('Error planificacion: ' + e.message, 0);
    }
  }

  function _fmtG(g){
    // Normalizado: SIEMPRE en gramos con separador de miles (acordado con Alejandro).
    if(g === null || g === undefined) return '—';
    var n = Math.round(Number(g) || 0);
    return n.toLocaleString('es-CO') + ' g';
  }

  function _renderPlanificacion(d){
    var meses=d.meses||2;
    var dias =d.dias ||_planDias;
    var horizonteLabel = d.horizonte_label || (dias+' días');

    // Cards resumen
    var cards=[
      {val:d.total_prods,    label:'Producciones<br>en calendario', icon:'&#128197;', color:'#1a4a7a'},
      {val:d.mps_deficit?d.mps_deficit.length:0, label:'MPs en<br>déficit', icon:'&#128997;', color:d.mps_deficit&&d.mps_deficit.length?'#dc3545':'#28a745'},
      {val:d.mps_ok_count||0, label:'MPs con stock<br>suficiente', icon:'&#10003;', color:'#28a745'},
      {val:d.bulk_opps?d.bulk_opps.length:0, label:'Oportunidades<br>de bulk', icon:'&#128200;', color:'#0d47a1'},
    ];
    document.getElementById('plan-cards').innerHTML=cards.map(function(c){
      return '<div style="background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.08);border-top:3px solid '+c.color+'">'
        +'<div style="font-size:22px;margin-bottom:4px">'+c.icon+'</div>'
        +'<div style="font-size:26px;font-weight:800;color:'+c.color+'">'+c.val+'</div>'
        +'<div style="font-size:11px;color:#666;margin-top:4px;line-height:1.4">'+c.label+'</div>'
        +'</div>';
    }).join('');

    // Producciones en horizonte
    if(d.producciones&&d.producciones.length){
      document.getElementById('plan-prods-box').style.display='block';
      var byMes={};
      d.producciones.forEach(function(p){ byMes[p.mes]=byMes[p.mes]||[]; byMes[p.mes].push(p); });
      var html='';
      Object.keys(byMes).sort().forEach(function(mes){
        html+='<div style="margin-bottom:8px;width:100%"><span style="font-size:11px;font-weight:700;color:#1a4a7a;text-transform:uppercase;letter-spacing:1px">'+mes+'</span><div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:4px">';
        byMes[mes].forEach(function(p){
          html+='<span style="background:#e8f0fe;color:#1a4a7a;border-radius:5px;padding:3px 10px;font-size:12px;font-weight:600">'+p.producto+' ('+p.kg+' kg)</span>';
        });
        html+='</div></div>';
      });
      document.getElementById('plan-prods-list').innerHTML=html||'Sin producciones identificadas en el calendario';
    }

    // Vista por producción: cada producción con su MP status
    if(d.producciones && d.producciones.length){
      document.getElementById('plan-prods-detail-box').style.display='block';
      var detailHtml=d.producciones.map(function(p, idx){
        var statusBadge = p.puede_producir
          ? '<span style="background:#d4edda;color:#155724;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700">&#10003; Puede producir</span>'
          : '<span style="background:#f8d7da;color:#721c24;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700">&#9888; Faltan '+p.n_mps_falta+' MP(s)</span>';
        var fechaStr = p.fecha || '';
        var producerHeader = '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;cursor:pointer" onclick="_toggleProdDetail('+idx+')">'
          +'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
          +'<span id="plan-prod-arrow-'+idx+'" style="color:#1a4a7a;font-size:12px">&#9654;</span>'
          +'<strong style="font-size:13px;color:#1a4a7a">'+p.producto+'</strong>'
          +'<span style="font-size:11px;color:#666">'+fechaStr+' &middot; '+p.kg+' kg</span>'
          +'</div>'+statusBadge+'</div>';
        var alcanzanList = (p.mps_status||[]).filter(function(m){return m.alcanza;});
        var faltanList   = (p.mps_status||[]).filter(function(m){return !m.alcanza;});
        var faltanHtml=faltanList.map(function(m){
          var stockTxt = m.ilimitado ? '∞ (producido en sitio)' : _fmtG(m.stock_g);
          return '<tr style="background:#fff5f5;border-bottom:1px solid #fadcdc">'
            +'<td style="padding:6px 8px;font-size:11px"><span style="color:#dc3545">&#9888;</span> '+m.nombre+'<span style="color:#aaa;font-size:10px;margin-left:4px;font-family:monospace">'+m.material_id+'</span></td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right">'+_fmtG(m.necesario_g)+'</td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right;color:#dc3545">'+stockTxt+'</td>'
            +'<td style="padding:6px 8px;font-size:11px;text-align:right;font-weight:700;color:#dc3545">'+_fmtG(m.deficit_g)+'</td>'
            +'</tr>';
        }).join('');
        var alcanzanHtml=alcanzanList.map(function(m){
          var stockTxt = m.ilimitado ? '∞' : _fmtG(m.stock_g);
          return '<tr style="border-bottom:1px solid #eee">'
            +'<td style="padding:5px 8px;font-size:11px"><span style="color:#28a745">&#10003;</span> '+m.nombre+'<span style="color:#aaa;font-size:10px;margin-left:4px;font-family:monospace">'+m.material_id+'</span></td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right">'+_fmtG(m.necesario_g)+'</td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right;color:#28a745">'+stockTxt+'</td>'
            +'<td style="padding:5px 8px;font-size:11px;text-align:right;color:#aaa">—</td>'
            +'</tr>';
        }).join('');
        var detailBody=''
          +'<div id="plan-prod-detail-'+idx+'" style="display:none;margin-top:10px;background:#fafbfc;border-radius:6px;padding:10px;border:1px solid #e8eaed">'
          + (faltanHtml ? '<div style="font-size:11px;font-weight:700;color:#dc3545;margin-bottom:4px">&#128997; Faltantes ('+faltanList.length+')</div>'
              +'<table style="width:100%;border-collapse:collapse;margin-bottom:10px"><thead><tr style="background:#fceaea;color:#721c24"><th style="padding:5px 8px;text-align:left;font-size:11px">MP</th><th style="padding:5px 8px;text-align:right;font-size:11px">Necesario</th><th style="padding:5px 8px;text-align:right;font-size:11px">Stock</th><th style="padding:5px 8px;text-align:right;font-size:11px">Falta</th></tr></thead><tbody>'+faltanHtml+'</tbody></table>'
              : '')
          + (alcanzanHtml ? '<div style="font-size:11px;font-weight:700;color:#155724;margin-bottom:4px">&#10003; MPs suficientes ('+alcanzanList.length+')</div>'
              +'<table style="width:100%;border-collapse:collapse"><thead><tr style="background:#e8f5e9;color:#155724"><th style="padding:5px 8px;text-align:left;font-size:11px">MP</th><th style="padding:5px 8px;text-align:right;font-size:11px">Necesario</th><th style="padding:5px 8px;text-align:right;font-size:11px">Stock</th><th style="padding:5px 8px;text-align:right;font-size:11px">—</th></tr></thead><tbody>'+alcanzanHtml+'</tbody></table>'
              : '')
          +'</div>';
        var bgColor = p.puede_producir ? '#fff' : '#fff8f8';
        var brColor = p.puede_producir ? '#28a745' : '#dc3545';
        return '<div style="background:'+bgColor+';border:1px solid #e0e0e0;border-left:4px solid '+brColor+';border-radius:6px;padding:10px 14px;margin-bottom:8px">'
          +producerHeader+detailBody+'</div>';
      }).join('');
      document.getElementById('plan-prods-detail-list').innerHTML=detailHtml;
    }

    // Staff general de MPs (todos los MPs con su estado)
    _renderStaffGeneral();

    // Tabla de déficit
    if(d.mps_deficit&&d.mps_deficit.length){
      document.getElementById('plan-deficit-box').style.display='block';
      var rows=d.mps_deficit.map(function(mp){
        var pct=mp.cobertura_pct;
        var pctColor=pct<30?'#dc3545':pct<70?'#fd7e14':'#28a745';
        var origenIcon=mp.origen==='china'?'&#127464;&#127475;':mp.origen==='colombia'?'&#127464;&#127476;':'&#127758;';
        return '<tr style="border-bottom:1px solid #eee">'
          +'<td style="padding:8px"><div style="font-weight:600;font-size:12px">'+mp.nombre+'</div>'
          +'<div style="font-size:10px;color:#888;font-family:monospace">'+mp.material_id+'</div></td>'
          +'<td style="padding:8px;font-size:12px;cursor:pointer;border-radius:4px" data-mid="'+mp.material_id+'" onclick="_editProv(this)" title="Clic para editar proveedor">'+origenIcon+' '+(mp.proveedor||'<em style="color:#bbb;font-size:11px">Sin asignar</em>')+'<span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span></td>'
          +'<td style="padding:8px;text-align:right;font-size:12px">'+_fmtG(mp.total_g)+'</td>'
          +'<td style="padding:8px;text-align:right;font-size:12px;color:'+(mp.stock_g<mp.total_g?'#dc3545':'#28a745')+'">'+_fmtG(mp.stock_g)+'</td>'
          +'<td style="padding:8px;text-align:right;font-weight:700;color:#dc3545;font-size:12px">'+_fmtG(mp.deficit_g)+'</td>'
          +'<td style="padding:8px;text-align:center"><div style="display:inline-block;background:#f0f0f0;border-radius:10px;overflow:hidden;width:80px;height:12px;margin-bottom:2px"><div style="background:'+pctColor+';width:'+pct+'%;height:100%"></div></div><div style="font-size:11px;color:'+pctColor+';font-weight:700">'+pct+'%</div></td>'
          +'<td style="padding:8px;text-align:center"><span style="background:#e8f0fe;color:#1a4a7a;border-radius:10px;padding:2px 8px;font-size:11px;font-weight:700">'+mp.n_meses+'m</span></td>'
          +'<td style="padding:8px;font-size:11px;color:#555;max-width:160px">'+mp.productos.join(', ')+'</td>'
          +'</tr>';
      }).join('');
      document.getElementById('plan-deficit-tbody').innerHTML=rows;
    }

    // MPs OK
    if(d.mps_ok_count>0){
      document.getElementById('plan-ok-box').style.display='block';
      // Construir lista desde mps del backend que no están en deficit
      // (solo mostramos count ya que la lista puede ser grande)
      document.getElementById('plan-ok-list').innerHTML='<span style="font-size:13px;color:#155724">'+d.mps_ok_count+' materias primas tienen stock suficiente para cubrir todas las producciones del período.</span>';
    }

    // Bulk opportunities
    if(d.bulk_opps&&d.bulk_opps.length){
      document.getElementById('plan-bulk-box').style.display='block';
      var bulkHtml=d.bulk_opps.map(function(mp){
        var origenBadge=mp.origen==='china'
          ?'<span style="background:#fff3e0;color:#e65100;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">&#127464;&#127475; Importación</span>'
          :'<span style="background:#e8f5e9;color:#1b5e20;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700">&#127464;&#127476; Local</span>';
        return '<div style="background:#fff;border:1px solid #c5d8fa;border-radius:8px;padding:14px;margin-bottom:10px;border-left:4px solid #0d47a1">'
          +'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">'
          +'<div><div style="font-weight:700;font-size:13px;color:#0d47a1">'+mp.nombre+'</div>'
          +'<div style="font-size:11px;color:#888;margin-top:2px">Proveedor: '+(mp.proveedor||'Sin asignar')+' &nbsp;|&nbsp; Usada en: '+mp.productos.join(', ')+'</div></div>'
          +origenBadge+'</div>'
          +'<div style="margin-top:8px;font-size:12px;color:#1a4a7a;background:#e8f0fe;border-radius:5px;padding:8px">&#128161; '+mp.bulk_msg+'</div>'
          +'<div style="margin-top:6px;display:flex;gap:12px;font-size:11px;color:#555">'
          +'<span>Total necesario: <strong>'+_fmtG(mp.total_g)+'</strong></span>'
          +'<span>Stock actual: <strong>'+_fmtG(mp.stock_g)+'</strong></span>'
          +'<span>Déficit: <strong style="color:#dc3545">'+_fmtG(mp.deficit_g)+'</strong></span>'
          +'<span>Meses de uso: <strong>'+mp.n_meses+'</strong></span>'
          +'</div></div>';
      }).join('');
      document.getElementById('plan-bulk-list').innerHTML=bulkHtml;
    }

    if(!d.total_prods){
      document.getElementById('plan-empty').style.display='block';
      document.getElementById('plan-empty').innerHTML='<div style="font-size:40px;margin-bottom:12px">&#128197;</div>'
        +'<div style="font-size:14px;font-weight:600;margin-bottom:6px">Sin producciones en el calendario para este período</div>'
        +'<div style="font-size:13px;color:#aaa">Verifica que los eventos de Google Calendar tengan el código SKU en el título (ej: NPHA – Fabricacion 14 kg)</div>';
    }
  }

  function exportarPlanificacion(){
    if(!_planData||!_planData.mps_deficit) return;
    var rows=[['Material','Codigo','Proveedor','Necesario_g','Stock_g','Deficit_g','Cobertura_pct','Meses_uso','Productos']];
    _planData.mps_deficit.forEach(function(mp){
      rows.push([mp.nombre,mp.material_id,mp.proveedor,mp.total_g,mp.stock_g,mp.deficit_g,mp.cobertura_pct,mp.n_meses,mp.productos.join('|')]);
    });
    var csv=rows.map(function(r){return r.map(function(c){return '"'+String(c||'').replace(/"/g,'""')+'"';}).join(',');}).join('\\n');
    var blob=new Blob([csv],{type:'text/csv'});
    var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
    a.download='planificacion_mps_'+_planDias+'d_'+new Date().toISOString().slice(0,10)+'.csv';
    a.click();
  }

  async function descargarChecklistVerificacion(){
    var btn=document.getElementById('btn-checklist-verif');
    if(btn){ btn.disabled=true; btn.textContent='Generando...'; }
    try{
      var resp=await fetch('/api/programacion/planificacion/checklist-verificacion?horizontes=15,30');
      if(!resp.ok){
        var err=await resp.json().catch(function(){return {error:'error '+resp.status};});
        _toast('Error: '+(err.error||'desconocido'),0);
        if(btn){ btn.disabled=false; btn.innerHTML='&#128203; Excel para verificar (15d + 1m)'; }
        return;
      }
      var blob=await resp.blob();
      var url=URL.createObjectURL(blob);
      var a=document.createElement('a');
      a.href=url;
      a.download='verificar_bodega_15-30d_'+new Date().toISOString().slice(0,10)+'.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      _toast('Excel descargado — listo para mandar a la asistente',1);
    }catch(e){
      _toast('Error: '+e.message,0);
    }finally{
      if(btn){ btn.disabled=false; btn.innerHTML='&#128203; Excel para verificar (15d + 1m)'; }
    }
  }

  function _toggleProdDetail(idx){
    var box=document.getElementById('plan-prod-detail-'+idx);
    var arr=document.getElementById('plan-prod-arrow-'+idx);
    if(!box) return;
    var open = box.style.display==='block';
    box.style.display = open ? 'none' : 'block';
    if(arr) arr.innerHTML = open ? '&#9654;' : '&#9660;';
  }

  function _renderStaffGeneral(){
    if(!_planData) return;
    var deficit = (_planData.mps_deficit||[]).map(function(mp){return Object.assign({}, mp, {_estado:'deficit'});});
    var ok      = (_planData.mps_ok     ||[]).map(function(mp){return Object.assign({}, mp, {_estado:'ok'});});
    var todos   = deficit.concat(ok);
    if(!todos.length){
      document.getElementById('plan-staff-box').style.display='none';
      return;
    }
    document.getElementById('plan-staff-box').style.display='block';
    var fEl=document.getElementById('plan-staff-filter');
    var sEl=document.getElementById('plan-staff-state');
    var filtro=(fEl&&fEl.value||'').trim().toLowerCase();
    var estadoF=(sEl&&sEl.value||'todos');
    var visibles = todos.filter(function(mp){
      if(estadoF==='deficit' && mp._estado!=='deficit') return false;
      if(estadoF==='ok'      && mp._estado!=='ok')      return false;
      if(filtro){
        var t=(mp.nombre+' '+mp.material_id+' '+(mp.proveedor||'')).toLowerCase();
        if(t.indexOf(filtro)===-1) return false;
      }
      return true;
    });
    // Ordenar: déficit primero, luego por nombre
    visibles.sort(function(a,b){
      if(a._estado!==b._estado) return a._estado==='deficit' ? -1 : 1;
      return (a.nombre||'').localeCompare(b.nombre||'');
    });
    if(!visibles.length){
      document.getElementById('plan-staff-tbody').innerHTML='';
      document.getElementById('plan-staff-empty').style.display='block';
      return;
    }
    document.getElementById('plan-staff-empty').style.display='none';
    var rows=visibles.map(function(mp){
      var pct=mp.cobertura_pct||0;
      var pctColor=pct<30?'#dc3545':pct<70?'#fd7e14':'#28a745';
      var estadoBadge = mp._estado==='deficit'
        ? '<span style="background:#f8d7da;color:#721c24;border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700">DÉFICIT</span>'
        : '<span style="background:#d4edda;color:#155724;border-radius:10px;padding:2px 8px;font-size:10px;font-weight:700">OK</span>';
      var rowBg = mp._estado==='deficit' ? '#fff8f8' : '#fff';
      return '<tr style="background:'+rowBg+';border-bottom:1px solid #eee">'
        +'<td style="padding:7px 8px;text-align:center">'+estadoBadge+'</td>'
        +'<td style="padding:7px 8px"><div style="font-weight:600;font-size:12px">'+mp.nombre+'</div><div style="font-size:10px;color:#888;font-family:monospace">'+mp.material_id+'</div></td>'
        +'<td style="padding:7px 8px;font-size:11px;color:#555">'+(mp.proveedor||'<em style="color:#bbb">Sin asignar</em>')+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px">'+_fmtG(mp.total_g)+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px;color:'+(mp.stock_g<mp.total_g?'#dc3545':'#28a745')+'">'+_fmtG(mp.stock_g)+'</td>'
        +'<td style="padding:7px 8px;text-align:right;font-size:12px;font-weight:'+(mp.deficit_g>0?'700':'400')+';color:'+(mp.deficit_g>0?'#dc3545':'#aaa')+'">'+(mp.deficit_g>0?_fmtG(mp.deficit_g):'—')+'</td>'
        +'<td style="padding:7px 8px;text-align:center"><div style="display:inline-block;background:#f0f0f0;border-radius:10px;overflow:hidden;width:60px;height:8px"><div style="background:'+pctColor+';width:'+pct+'%;height:100%"></div></div><div style="font-size:10px;color:'+pctColor+';font-weight:700">'+pct+'%</div></td>'
        +'<td style="padding:7px 8px;font-size:10px;color:#666;max-width:140px">'+(mp.productos||[]).slice(0,3).join(', ')+((mp.productos||[]).length>3?' +'+((mp.productos||[]).length-3):'')+'</td>'
        +'</tr>';
    }).join('');
    document.getElementById('plan-staff-tbody').innerHTML=rows;
  }

  async function solicitarBloque(){
    if(!_planData||!_planData.mps_deficit||!_planData.mps_deficit.length){
      _toast('No hay MPs en déficit para el período actual',0); return;
    }
    var nDef=_planData.mps_deficit.length;
    var label=_planData.horizonte_label||(_planDias+' días');
    if(!confirm('¿Crear solicitudes de compra agrupadas por proveedor para '+nDef+' MPs en déficit ('+label+')?\\n\\nSe creará 1 solicitud por proveedor con todos sus MPs faltantes. Esto queda registrado en audit log.')) return;
    var btn=document.getElementById('btn-solicitar-bloque');
    if(btn){ btn.disabled=true; btn.textContent='Creando...'; }
    try{
      var resp=await fetch('/api/programacion/planificacion/solicitar-bulk',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({dias:_planDias, urgencia:'Normal'})
      });
      var data=await resp.json();
      if(btn){ btn.disabled=false; btn.innerHTML='&#128229; Solicitar en bloque'; }
      if(!resp.ok || data.error){
        _toast('Error: '+(data.error||'desconocido'),0);
        return;
      }
      var n=data.count_solicitudes||0;
      var nE=data.count_errores||0;
      var msg = n+' solicitud(es) creadas';
      if(data.solicitudes_creadas && data.solicitudes_creadas.length){
        var nums=data.solicitudes_creadas.map(function(s){return s.numero;}).join(', ');
        msg += ' ('+nums+')';
      }
      if(nE) msg += ' · '+nE+' errores';
      _toast(msg, n>0?1:0);
    }catch(e){
      if(btn){ btn.disabled=false; btn.innerHTML='&#128229; Solicitar en bloque'; }
      _toast('Error: '+e.message, 0);
    }
  }

  async function solicitarNecesidades(){
    if(!_planData||!_planData.mps_deficit||!_planData.mps_deficit.length){
      _toast('No hay MPs en déficit para el período actual',0); return;
    }
    var deficit = _planData.mps_deficit;
    // Agrupar por proveedor
    var grupos = {};
    deficit.forEach(function(mp){
      var prov = (mp.proveedor||'').trim() || 'Sin asignar';
      if(!grupos[prov]) grupos[prov] = [];
      grupos[prov].push(mp);
    });
    var proveedores = Object.keys(grupos);
    var btn = document.getElementById('btn-solicitar');
    if(btn){ btn.disabled=true; btn.textContent='Creando...'; }
    var creadas = [];
    var errores = [];
    var hoy = new Date(); hoy.setDate(hoy.getDate()+7);
    var fechaReq = hoy.toISOString().slice(0,10);
    for(var i=0;i<proveedores.length;i++){
      var prov = proveedores[i];
      var mps  = grupos[prov];
      var items = mps.map(function(mp){
        var deficit_g = Math.ceil(mp.deficit_g);
        return {
          codigo_mp: mp.material_id||'',
          nombre_mp: mp.nombre||'',
          cantidad_g: deficit_g,
          unidad: 'g',
          justificacion: 'Planificación '+_planDias+'d — Para producir: '+mp.productos.slice(0,3).join(', ')+(mp.productos.length>3?' +'+(mp.productos.length-3)+' más':''),
          valor_estimado: 0
        };
      });
      // Resumen de MPs principales para que el card de solicitudes muestre
      // exactamente qué se está pidiendo, no solo el conteo.
      var mpsResumen = mps.slice(0, 5).map(function(mp){
        return mp.nombre + ' (' + Math.ceil(mp.deficit_g).toLocaleString('es-CO') + ' g)';
      }).join(', ');
      if(mps.length > 5) mpsResumen += ' +' + (mps.length-5) + ' más';
      var payload = {
        solicitante: 'sebastian',
        urgencia: 'Normal',
        observaciones: 'Planificación Estratégica '+_planDias+'d · Proveedor: '+prov+' · '+mps.length+' MPs · '+mpsResumen,
        area: 'Produccion',
        empresa: 'Espagiria',
        categoria: 'Materia Prima',
        tipo: 'Compra',
        fecha_requerida: fechaReq,
        items: items
      };
      try{
        var resp = await fetch('/api/solicitudes-compra',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(payload)
        });
        var data = await resp.json();
        if(resp.ok && data.numero){
          creadas.push(data.numero);
        } else {
          errores.push(prov+': '+(data.error||'error desconocido'));
        }
      } catch(e){
        errores.push(prov+': '+e.message);
      }
    }
    if(btn){ btn.disabled=false; btn.innerHTML='&#128722; Solicitar necesidades'; }
    if(creadas.length){
      var msg = creadas.length===1
        ? 'Solicitud '+creadas[0]+' creada en Compras ('+deficit.length+' MPs)'
        : creadas.length+' solicitudes creadas: '+creadas.join(', ');
      _toast(msg, 1);
    }
    if(errores.length){
      _toast('Errores: '+errores.join(' | '), 0);
    }
  }

  function _editProv(td){
    var mid  = td.dataset.mid;
    var cur  = td.innerText.replace('✎','').trim();
    if(cur === 'Sin asignar') cur = '';
    var input = document.createElement('input');
    input.value = cur;
    input.style.cssText = 'width:120px;padding:3px 6px;border:2px solid #1a4a7a;border-radius:4px;font-size:12px;outline:none';
    input.onclick = function(e){ e.stopPropagation(); };
    td.innerHTML = '';
    td.appendChild(input);
    input.focus();
    function save(){
      var prov = input.value.trim();
      if(!prov){ td.innerHTML = '&#127758; <em style="color:#bbb;font-size:11px">Sin asignar</em><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>'; return; }
      td.innerHTML = '<span style="color:#999;font-size:11px">Guardando...</span>';
      fetch('/api/maestro-mps/'+mid+'/proveedor',{
        method:'PUT', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({proveedor:prov})
      }).then(function(r){return r.json();}).then(function(d){
        if(d.ok||d.message){
          td.innerHTML = '&#127758; '+prov+'<span style="color:#28a745;font-size:10px;margin-left:4px">&#10003;</span><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>';
          td.dataset.mid = mid;
          td.onclick = function(){ _editProv(td); };
          // Update bulk opps panel too
          if(_planData&&_planData.bulk_opps){
            _planData.bulk_opps.forEach(function(mp){ if(mp.material_id===mid) mp.proveedor=prov; });
          }
          _toast('Proveedor actualizado: '+prov, 1);
        } else {
          td.innerHTML = '&#127758; '+prov+'<span style="color:#dc3545;font-size:10px;margin-left:4px">&#10007;</span><span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>';
          _toast('Error al guardar: '+(d.error||''), 0);
        }
        td.dataset.mid = mid;
        td.onclick = function(){ _editProv(td); };
      }).catch(function(e){
        td.innerHTML = '&#127758; '+prov+'<span style="color:#dc3545;font-size:10px;margin-left:4px">&#10007;</span>';
        _toast('Error: '+e.message, 0);
      });
    }
    input.addEventListener('blur', save);
    input.addEventListener('keydown', function(e){
      if(e.key==='Enter'){ e.preventDefault(); input.blur(); }
      if(e.key==='Escape'){ td.innerHTML = '&#127758; '+(cur||'<em style="color:#bbb;font-size:11px">Sin asignar</em>')+'<span style="color:#ccc;font-size:10px;margin-left:3px">&#9998;</span>'; td.dataset.mid=mid; td.onclick=function(){_editProv(td);}; }
    });
  }

  async function guardarProgramacion() {
    var producto = document.getElementById('mp-producto').value;
    var fecha    = document.getElementById('mp-fecha').value;
    var lotes    = parseInt(document.getElementById('mp-lotes').value) || 1;
    var obs      = document.getElementById('mp-obs').value;
    if(!fecha){ alert('Selecciona una fecha'); return; }
    try{
      var r = await fetch('/api/programacion/programar', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({producto:producto, fecha:fecha, lotes:lotes, observaciones:obs})
      });
      var d = await r.json();
      if(!d.ok){ alert('Error: '+(d.error||'desconocido')); return; }
      // Si hay sala u operario seleccionado, persistir asignacion
      var asign = {};
      var sala = document.getElementById('mp-sala').value;
      var disp = document.getElementById('mp-op-disp').value;
      var elab = document.getElementById('mp-op-elab').value;
      var env  = document.getElementById('mp-op-env').value;
      var acon = document.getElementById('mp-op-acon').value;
      if(sala) asign.area_id                       = parseInt(sala);
      if(disp) asign.operario_dispensacion_id      = parseInt(disp);
      if(elab) asign.operario_elaboracion_id       = parseInt(elab);
      if(env)  asign.operario_envasado_id          = parseInt(env);
      if(acon) asign.operario_acondicionamiento_id = parseInt(acon);
      if(Object.keys(asign).length){
        var rA = await fetch('/api/programacion/programar/'+d.id+'/asignar', {
          method:'PATCH', headers:{'Content-Type':'application/json'},
          body: JSON.stringify(asign)
        });
        var dA = await rA.json();
        if(dA.warnings && dA.warnings.length){
          // No bloqueante — solo informativo
          console.warn('Conflicto asignacion:', dA.warnings);
        }
      }
      cerrarModalProgramar();
      actualizarDashboard();
    }catch(e){ alert('Error de red: '+e); }
  }

  function cargarEventosProducto(producto) {
    fetch('/api/programacion/programar').then(function(r){ return r.json(); }).then(function(eventos){
      var futuros = eventos.filter(function(e){
        return e.producto === producto && e.estado !== 'cancelado' && e.estado !== 'completado';
      });
      var lista = document.getElementById('mp-eventos-lista');
      var items = document.getElementById('mp-eventos-items');
      if(futuros.length === 0){ lista.style.display='none'; return; }
      lista.style.display = 'block';
      items.innerHTML = futuros.map(function(ev){
        var estadoColor = ev.estado === 'pendiente' ? '#0d6efd' : '#fd7e14';
        // Badges sala + operarios asignados (post-INVIMA)
        var asignadoBits = [];
        if(ev.area_nombre) asignadoBits.push('🏭 '+ev.area_nombre);
        if(ev.operario_dispensacion)      asignadoBits.push('Disp: '+ev.operario_dispensacion);
        if(ev.operario_elaboracion)       asignadoBits.push('Elab: '+ev.operario_elaboracion);
        if(ev.operario_envasado)          asignadoBits.push('Env: '+ev.operario_envasado);
        if(ev.operario_acondicionamiento) asignadoBits.push('Acon: '+ev.operario_acondicionamiento);
        var asignadoHTML = asignadoBits.length
          ? '<div style="font-size:11px;color:#475569;margin-top:4px;line-height:1.5">'+asignadoBits.map(function(b){
              return '<span style="background:#eef2ff;color:#3730a3;padding:1px 6px;border-radius:4px;margin-right:4px;display:inline-block;margin-bottom:2px">'+b+'</span>';
            }).join('')+'</div>'
          : '<div style="font-size:10px;color:#94a3b8;font-style:italic;margin-top:4px">Sin sala/operarios asignados</div>';
        return '<div style="padding:8px 0;border-bottom:1px solid #f5f5f5;font-size:12px">' +
          '<div style="display:flex;align-items:center;gap:8px">' +
            '<span style="flex:1;font-weight:600">'+ev.fecha+'</span>' +
            '<span style="color:#555">'+ev.lotes+' lote'+(ev.lotes>1?'s':'')+'</span>' +
            '<span style="background:'+estadoColor+';color:#fff;padding:2px 7px;border-radius:8px">'+ev.estado+'</span>' +
            '<button onclick="cancelarEvento('+ev.id+',\\''+producto+'\\')" style="background:#dc3545;color:#fff;border:none;border-radius:4px;padding:2px 7px;font-size:11px;cursor:pointer">✕</button>' +
          '</div>' +
          asignadoHTML +
          '</div>';
      }).join('');
    });
  }

  function cancelarEvento(id, producto) {
    if(!confirm('¿Cancelar esta producción programada?')) return;
    fetch('/api/programacion/programar/'+id, {method:'DELETE'})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok){ cargarEventosProducto(producto); actualizarDashboard(); }
      });
  }

  // ── MP Bridge UI ─────────────────────────────────────────────────────────
  function toggleBridgePanel(){
    var body = document.getElementById('bridge-panel-body');
    if(!body) return;
    body.style.display = body.style.display === 'none' ? 'block' : 'none';
  }

  async function cargarUnmatched(btn){
    var list = document.getElementById('unmatched-list');
    var cnt  = document.getElementById('unmatched-count');
    if(btn){ btn.disabled=true; btn.textContent='Cargando...'; }
    try {
      var r = await fetch('/api/programacion/mp-bridge/unmatched');
      var d = await r.json();
      if(cnt) cnt.textContent = '(' + d.total_unmatched + ' sin enlazar)';
      if(!d.unmatched || d.unmatched.length === 0){
        list.innerHTML = '<div style="color:#2B7A78;font-size:12px;padding:8px">✅ Todos los MPs de fórmulas tienen enlace o ya coinciden automáticamente.</div>';
      } else {
        list.innerHTML = d.unmatched.map(function(u){
          var cands = (u.candidates||[]).slice(0,5);
          var candHtml = cands.length === 0
            ? '<span style="color:#aaa;font-size:11px">Sin candidatos automáticos</span>'
            : cands.map(function(c){
                var safeF = encodeURIComponent(JSON.stringify({
                  formula_material_id: u.formula_material_id,
                  formula_material_nombre: u.formula_material_nombre,
                  bodega_material_id: c.material_id,
                  bodega_material_nombre: c.material_nombre
                }));
                return '<button onclick="linkBridge(this,' + "'" + safeF + "')" + '" style="background:#f0f4ff;border:1px solid #c5cef9;border-radius:4px;padding:3px 8px;font-size:11px;cursor:pointer;margin:2px">' +
                  c.material_id + ' — ' + (c.material_nombre||'').substring(0,30) +
                  ' (' + c.shared_keywords.join(',') + ')' +
                  '</button>';
              }).join('');
          return '<div style="border:1px solid #e8d5c0;border-radius:6px;padding:10px;margin-bottom:8px;background:#fffaf5">' +
            '<div style="font-size:12px;font-weight:600;color:#5c3317;margin-bottom:6px">' +
              u.formula_material_id + ' — ' + u.formula_material_nombre +
            '</div>' +
            '<div style="font-size:11px;color:#666;margin-bottom:6px">Candidatos: ' + candHtml + '</div>' +
            '<div style="display:flex;gap:6px;flex-wrap:wrap">' +
              '<input id="fid-' + u.formula_material_id + '" placeholder="ID Bodega (ej: MP00293)" ' +
                'style="border:1px solid #ccc;border-radius:4px;padding:3px 7px;font-size:11px;width:160px">' +
              '<input id="fn-' + u.formula_material_id + '" placeholder="Nombre bodega (opcional)" ' +
                'style="border:1px solid #ccc;border-radius:4px;padding:3px 7px;font-size:11px;width:200px">' +
              '<button onclick="linkBridgeManual(this,' + "'" + u.formula_material_id + "','" + u.formula_material_nombre.replace(/'/g,"") + "')" + '" ' +
                'style="background:#5c3317;color:#fff;border:none;border-radius:4px;padding:3px 10px;font-size:11px;cursor:pointer">Enlazar</button>' +
            '</div>' +
          '</div>';
        }).join('');
      }
    } catch(e) {
      if(list) list.innerHTML = '<div style="color:#c00;font-size:12px">Error: ' + e.message + '</div>';
    }
    if(btn){ btn.disabled=false; btn.textContent='\u21BA Cargar'; }
  }

  async function linkBridge(btn, safePayload){
    var payload;
    try { payload = JSON.parse(decodeURIComponent(safePayload)); } catch(e){ alert('Error decodificando payload'); return; }
    btn.disabled=true; btn.style.background='#c5cef9';
    var r = await fetch('/api/programacion/mp-bridge', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    var d = await r.json();
    if(d.ok){
      _toast('Enlazado: ' + payload.formula_material_id + ' \u2192 ' + payload.bodega_material_id, 1);
      cargarUnmatched(null);
      cargarBridgeMappings();
    } else {
      _toast('Error: ' + (d.error||'desconocido'), 0);
      btn.disabled=false;
    }
  }

  async function linkBridgeManual(btn, fid, fname){
    var bidEl = document.getElementById('fid-' + fid);
    var bnameEl = document.getElementById('fn-' + fid);
    var bid = bidEl ? bidEl.value.trim() : '';
    var bname = bnameEl ? bnameEl.value.trim() : '';
    if(!bid){ alert('Ingresa el ID de Bodega (ej: MP00293)'); return; }
    btn.disabled=true;
    var r = await fetch('/api/programacion/mp-bridge', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        formula_material_id: fid,
        formula_material_nombre: fname,
        bodega_material_id: bid,
        bodega_material_nombre: bname
      })
    });
    var d = await r.json();
    if(d.ok){
      _toast('Enlazado: ' + fid + ' \u2192 ' + bid, 1);
      cargarUnmatched(null);
      cargarBridgeMappings();
    } else {
      _toast('Error: ' + (d.error||'desconocido'), 0);
    }
    btn.disabled=false;
  }

  async function cargarBridgeMappings(){
    var el = document.getElementById('bridge-mappings-list');
    if(!el) return;
    var r = await fetch('/api/programacion/mp-bridge');
    var rows = await r.json();
    var active = rows.filter(function(x){ return x.activo; });
    if(active.length === 0){
      el.innerHTML = '<div style="color:#aaa;font-style:italic;font-size:12px">— sin mapeos activos —</div>';
      return;
    }
    el.innerHTML = '<table style="width:100%;border-collapse:collapse;font-size:12px">' +
      '<thead><tr style="background:#f5f5f5">' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Formula ID</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Formula Nombre</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Bodega ID</th>' +
        '<th style="text-align:left;padding:5px 8px;border-bottom:1px solid #ddd">Bodega Nombre</th>' +
        '<th style="padding:5px 8px;border-bottom:1px solid #ddd"></th>' +
      '</tr></thead>' +
      '<tbody>' +
      active.map(function(m){
        return '<tr style="border-bottom:1px solid #f0f0f0">' +
          '<td style="padding:5px 8px;font-family:monospace;color:#5c3317">' + m.formula_material_id + '</td>' +
          '<td style="padding:5px 8px">' + (m.formula_material_nombre||'—') + '</td>' +
          '<td style="padding:5px 8px;font-family:monospace;color:#2B7A78">' + m.bodega_material_id + '</td>' +
          '<td style="padding:5px 8px">' + (m.bodega_material_nombre||'—') + '</td>' +
          '<td style="padding:5px 8px">' +
            '<button onclick="eliminarBridge(' + m.id + ')" ' +
              'style="background:#dc3545;color:#fff;border:none;border-radius:3px;padding:2px 7px;font-size:10px;cursor:pointer">✕</button>' +
          '</td>' +
        '</tr>';
      }).join('') +
      '</tbody></table>';
  }

  async function eliminarBridge(id){
    if(!confirm('¿Eliminar este enlace?')) return;
    var r = await fetch('/api/programacion/mp-bridge/' + id, {method:'DELETE'});
    var d = await r.json();
    if(d.ok){ _toast('Enlace eliminado', 1); cargarBridgeMappings(); cargarUnmatched(null); }
  }
  </script>

</body>
</html>
"""
