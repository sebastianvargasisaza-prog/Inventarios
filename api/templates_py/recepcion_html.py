# recepcion_html.py - extraído de index.py (Fase C prep)
RECEPCION_HTML = r"""
<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Recepcion de Mercancia - Espagiria</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
:root{--vio:#6d28d9;--vio2:#7c3aed;--viod:#5b21b6;--ink:#1e1b2e;--mut:#6b7280;--line:#ece9f6;--bg:#f6f5fb;--card:#fff;--soft:#faf8ff;--amber:#f59e0b;--green:#16a34a;--red:#dc2626;}
:root[data-theme="dark"]{--ink:#e8e6f2;--mut:#a5a1b8;--line:#2a2740;--bg:#131022;--card:#1b1830;--soft:#211d38;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--ink);font-size:14px;}
.container{max-width:1800px;width:96vw;margin:0 auto;padding:22px 20px 64px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px 24px;margin-bottom:22px;box-shadow:0 4px 24px rgba(76,29,149,.06);}
.card h2{font-size:16.5px;font-weight:800;letter-spacing:-.01em;margin-bottom:16px;color:var(--ink);display:flex;align-items:center;gap:9px;padding-left:12px;border-left:4px solid var(--vio);line-height:1.15;}
.oc-queue{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:13px;margin-bottom:8px;}
.oc-card{position:relative;background:var(--card);border:1px solid var(--line);border-left:5px solid #cbd5e1;border-radius:14px;padding:13px 15px;cursor:pointer;transition:transform .14s ease,box-shadow .16s ease;box-shadow:0 2px 10px rgba(76,29,149,.05);}
.oc-card:hover{box-shadow:0 13px 30px rgba(124,58,237,.16);transform:translateY(-3px);}
.oc-card .oc-num{font-weight:800;font-size:13.5px;color:var(--viod);letter-spacing:-.01em;}
.oc-card .oc-prov{font-size:12px;color:var(--mut);margin-top:3px;font-weight:600;}
.oc-card .oc-val{font-size:13px;color:var(--green);font-weight:800;margin-top:5px;}
.oc-card .oc-dias{font-size:11px;color:#a89fc0;margin-top:2px;}
.search-row{display:flex;gap:10px;align-items:center;margin-bottom:16px;}
.search-row input{flex:1;max-width:340px;padding:10px 14px;border:1px solid var(--line);border-radius:11px;font-size:14px;background:var(--card);color:var(--ink);}
.search-row input:focus{outline:none;border-color:var(--vio2);box-shadow:0 0 0 3px rgba(124,58,237,.12);}
.btn{padding:10px 20px;border:none;border-radius:11px;font-size:14px;cursor:pointer;font-weight:700;box-shadow:0 2px 8px rgba(76,29,149,.10);transition:transform .1s,box-shadow .15s,filter .15s;}
.btn:hover{transform:translateY(-1px);box-shadow:0 7px 18px rgba(76,29,149,.18);}
.btn-primary{background:linear-gradient(135deg,var(--vio2),var(--viod));color:#fff;}
.btn-primary:hover{filter:brightness(1.07);}
.btn-success{background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;}
.btn-success:hover{filter:brightness(1.06);}
.btn-print{background:linear-gradient(135deg,#3b82f6,#1e40af);color:#fff;}
.btn-print:hover{filter:brightness(1.06);}
.btn-env{padding:6px 11px;border:1px solid #ddd6fe;border-radius:9px;background:#f5f3ff;color:#5b21b6;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap;transition:background .12s,border-color .12s;}
.btn-env:hover{background:#ede9fe;border-color:#c4b5fd;}
.btn-env.multi{background:linear-gradient(135deg,#ede9fe,#ddd6fe);border-color:#a78bfa;color:#4c1d95;}
.btn-env:disabled{background:#f8fafc;color:#cbd5e1;border-color:#eef2f7;cursor:default;}
.oc-info{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;}
.oc-info .lbl{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px;font-weight:700;}
.oc-info .val{font-size:14px;font-weight:700;color:var(--ink);margin-top:2px;}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:800;}
.badge-autorizada{background:#fef3c7;color:#92400e;}
.badge-pagada{background:#d1fae5;color:#065f46;}
.badge-recibida{background:#dbeafe;color:#1e40af;}
.badge-borrador{background:#f3f4f6;color:#374151;}
table{width:100%;border-collapse:collapse;font-size:13px;}
th{background:var(--soft);padding:10px 9px;text-align:left;font-weight:800;color:var(--vio);text-transform:uppercase;font-size:10.5px;letter-spacing:.05em;border-bottom:2px solid var(--line);white-space:nowrap;}
td{padding:9px 9px;border-bottom:1px solid var(--line);vertical-align:middle;color:var(--ink);}
tr:hover td{background:var(--soft);}
td input[type=number]{width:76px;padding:6px 8px;border:1px solid var(--line);border-radius:7px;font-size:13px;background:var(--card);color:var(--ink);}
td input[type=number]:focus{outline:none;border-color:var(--vio2);box-shadow:0 0 0 3px rgba(124,58,237,.1);}
td select{padding:6px 9px;border:1px solid var(--line);border-radius:7px;font-size:13px;background:var(--card);color:var(--ink);}
td input[type=text]{width:100%;padding:6px 9px;border:1px solid var(--line);border-radius:7px;font-size:13px;background:var(--card);color:var(--ink);}
.row-ok td{background:#f0fdf4;}
.row-disc td{background:#fff7ed;}
.row-falta td{background:#fef2f2;}
.obs-row{margin-top:14px;}
.obs-row label{font-size:13px;font-weight:700;display:block;margin-bottom:6px;color:var(--ink);}
.obs-row textarea{width:100%;padding:10px 13px;border:1px solid var(--line);border-radius:10px;font-size:13px;resize:vertical;min-height:74px;background:var(--card);color:var(--ink);}
.obs-row textarea:focus{outline:none;border-color:var(--vio2);box-shadow:0 0 0 3px rgba(124,58,237,.1);}
.receptor-row{display:flex;gap:12px;align-items:center;margin-top:14px;}
.receptor-row label{font-size:13px;font-weight:700;white-space:nowrap;color:var(--ink);}
.receptor-row input{flex:1;max-width:270px;padding:9px 13px;border:1px solid var(--line);border-radius:10px;font-size:13px;background:var(--card);color:var(--ink);}
.submit-row{margin-top:18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
.msg{font-size:13px;padding:9px 15px;border-radius:9px;}
.msg-ok{background:#d1fae5;color:#065f46;}
.msg-err{background:#fee2e2;color:#991b1b;}
.tabs{display:flex;gap:4px;margin-bottom:18px;border-bottom:2px solid var(--line);flex-wrap:wrap;}
.tab-btn{padding:10px 18px;border:none;background:none;font-size:13px;font-weight:600;color:var(--mut);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;border-radius:8px 8px 0 0;transition:color .12s,background .12s;}
.tab-btn.active{color:var(--viod);border-bottom-color:var(--vio);font-weight:800;background:var(--soft);}
.tab-btn:hover{color:var(--viod);}
.tab-content{display:none;}
.tab-content.active{display:block;}
.empty{text-align:center;padding:34px;color:var(--mut);font-size:13px;}
.cnt-badge{display:inline-block;background:var(--vio);color:#fff;border-radius:20px;font-size:11px;font-weight:800;padding:1px 8px;margin-left:5px;}
.tab-btn.active .cnt-badge{background:var(--viod);}
.disc{color:#dc2626;font-weight:700;}
.valor{font-family:'Courier New',monospace;font-size:12px;font-weight:700;}
.progress-bar{background:var(--line);border-radius:4px;height:6px;margin-top:4px;}
.progress-fill{background:#16a34a;height:6px;border-radius:4px;transition:width .3s;}
.item-pct{font-size:11px;color:var(--mut);margin-top:2px;}
.icon-ok{color:#16a34a;font-size:16px;}
.icon-disc{color:#d97706;font-size:16px;}
.icon-falta{color:#dc2626;font-size:16px;}
</style>
</head>
<body>
<header class="cx-mod-header cx-fade-in">
  <span class="cx-mod-header__logo" style="display:inline-flex;align-items:center;color:#6d28d9;"><svg viewBox="0 0 32 32" width="38" height="38" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg"><circle cx="16" cy="12" r="3" fill="#6d28d9"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/></svg></span>
  <div>
    <div class="cx-mod-header__title">
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#6d28d9" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:6px"><path d="M14 18V6a2 2 0 00-2-2H4a2 2 0 00-2 2v11a1 1 0 001 1h2"/><path d="M15 18h-3M22 18h-2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><path d="M14 9h3l3 4v5h-2"/></svg>
      Recepción de Mercancía
    </div>
    <div class="cx-mod-header__sub"><strong>EOS</strong> &middot; ingreso de MP &amp; MEE desde OCs</div>
  </div>
  <div class="cx-mod-header__nav">
    <a href="/modulos" class="cx-btn cx-btn-ghost cx-btn-sm" title="Volver">&larr; Módulos</a>
    <button class="cx-theme-toggle" onclick="cxToggleTheme()" title="Modo claro/oscuro">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4"/></svg>
    </button>
  </div>
</header>
<script>function cxToggleTheme(){var h=document.documentElement;var c=h.getAttribute('data-theme');var n=c==='dark'?'light':'dark';if(n==='dark')h.setAttribute('data-theme','dark');else h.removeAttribute('data-theme');try{localStorage.setItem('cx-theme',n);}catch(e){}}</script>
<div class="container">

  <div class="card" style="background:linear-gradient(120deg,#f5f3ff,#faf5ff,#fff);border-left:4px solid #6d28d9;">
    <div style="font-size:13px;color:#44403c;line-height:1.6;">
      <b>&#128203; Esto es la recepci&oacute;n administrativa</b> de <b>materias primas y envases</b>: comprob&aacute;s que lleg&oacute; lo de la OC/factura y las cantidades. Lo t&eacute;cnico (an&aacute;lisis, liberaci&oacute;n) lo hace <b>Calidad</b> despu&eacute;s (F01/F02) &middot; el lote entra a <b>cuarentena</b> hasta que Calidad lo apruebe.<br>
      <span style="color:#78716c;font-size:12px;">Los <b>consumibles y gastos</b> (papeler&iacute;a, EPP, aseo, servicios) NO se reciben ac&aacute; &rarr; se manejan en <b>Cat&aacute;logo / Consumos</b>. Los <b>servicios</b> solo se pagan.</span>
    </div>
  </div>

  <div class="card">
    <h2>&#9203; OCs Pendientes de Recepcion</h2>
    <input type="text" oninput="filterByText('#queue-list .oc-card', this.value)" placeholder="&#128269; Buscar OC o proveedor…" style="width:100%;max-width:360px;padding:9px 13px;border:1px solid #e7e5e4;border-radius:10px;font-size:13px;margin-bottom:12px;box-shadow:0 1px 2px rgba(15,23,42,.04);">
    <div id="queue-list"><p style="color:#a8a29e;font-size:13px;">Cargando...</p></div>
  </div>

  <div class="card">
    <h2>&#128269; Registrar Recepcion</h2>
    <div class="search-row">
      <input type="text" id="oc-input" placeholder="Numero de OC (ej: OC-2026-001)" onkeydown="if(event.key==='Enter')buscarOC()">
      <button class="btn btn-primary" onclick="buscarOC()">Buscar OC</button>
    </div>
    <div id="oc-msg"></div>

    <div id="oc-section" style="display:none">
      <div class="oc-info" id="oc-header"></div>
      <div id="oc-estado-warn" style="display:none;margin:10px 0;padding:12px 16px;border-radius:6px;font-weight:600;"></div>
      <div style="overflow-x:auto;">
        <table>
          <thead>
            <tr>
              <th style="width:36px;"></th>
              <th style="width:64px;text-align:center;" title="Destildá una MP para NO recibirla ahora (queda pendiente para después)">Recibir</th>
              <th>Material</th>
              <th>Solicitado</th>
              <th>Cantidad Recibida</th>
              <th>Diferencia</th>
              <th>% Cumpl.</th>
              <th>Estado</th>
              <th>Lote</th>
              <th>Vence</th>
              <th>Notas</th>
              <th style="text-align:center;" title="¿En cuántos envases individuales llegó y cuánto hay en cada uno? Clic para definir (ej: 3500 g = 3 de 1000 + 1 de 500).">Envases</th>
              <th style="text-align:center;">Rótulo</th>
            </tr>
          </thead>
          <tbody id="items-body"></tbody>
        </table>
      </div>

      <div class="receptor-row">
        <label for="receptor-input">Recibido por:</label>
        <input type="text" id="receptor-input" placeholder="Tu nombre">
      </div>

      <div class="obs-row">
        <label>Observaciones generales:</label>
        <textarea id="obs-input" placeholder="Ej: Caja exterior golpeada pero producto en buen estado. Falto 1 item."></textarea>
      </div>

      <div class="submit-row">
        <button class="btn btn-success" onclick="registrarRecepcion()">&#10003; Registrar Recepcion</button>
        <div id="submit-msg"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>&#128202; Monitoreo: Pagado - Llego?</h2>
    <div class="tabs">
      <button class="tab-btn active" id="tab-btn-transito" onclick="showTab('transito')">
        En Transito <span class="cnt-badge" id="cnt-transito">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-parcial" onclick="showTab('parcial')">
        Parciales <span class="cnt-badge" id="cnt-parcial">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-recibidas" onclick="showTab('recibidas')">
        Recibidas <span class="cnt-badge" id="cnt-recibidas">0</span>
      </button>
      <button class="tab-btn" id="tab-btn-disc" onclick="showTab('disc')">
        Con Discrepancias <span class="cnt-badge" id="cnt-disc">0</span>
      </button>
    </div>
    <div id="tab-transito" class="tab-content active"></div>
    <div id="tab-parcial" class="tab-content"></div>
    <div id="tab-recibidas" class="tab-content"></div>
    <div id="tab-disc" class="tab-content"></div>
  </div>

  <div class="card">
    <h2>&#128269; Trazabilidad de Lote</h2>
    <div class="search-row">
      <input type="text" id="lote-input" placeholder="Numero de lote (ej: L-2026-001)" onkeydown="if(event.key==='Enter')buscarLote()">
      <button class="btn btn-primary" onclick="buscarLote()">Buscar</button>
    </div>
    <div id="lote-result" style="margin-top:12px;"></div>
  </div>

  <!-- Modal · Rótulos por recipiente (Laura 16-jul) -->
  <div id="rec-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:950;align-items:center;justify-content:center;padding:16px;">
    <div style="background:var(--card,#fff);border-radius:16px;max-width:560px;width:100%;box-shadow:0 24px 70px rgba(0,0,0,.35);overflow:hidden;">
      <div style="background:linear-gradient(135deg,#4c1d95,#6d28d9);color:#fff;padding:16px 22px;font-weight:800;font-size:15px;display:flex;justify-content:space-between;align-items:center;">
        <span>&#128230; Envases de este material</span>
        <button onclick="cerrarRecModal()" style="background:none;border:none;color:#e9d5ff;font-size:22px;cursor:pointer;line-height:1;">&times;</button>
      </div>
      <div style="padding:20px 22px;">
        <div id="rec-info" style="font-size:13px;color:var(--mut,#6b7280);margin-bottom:14px;"></div>
        <label style="font-size:12px;font-weight:700;color:var(--ink,#1e1b2e);">¿En cuántos envases individuales vino?</label><br>
        <input type="number" id="rec-n" min="1" max="60" value="1" oninput="recBuildInputs()" style="width:100px;padding:9px 12px;border:1px solid var(--line,#e5e7eb);border-radius:9px;margin:6px 0 14px;font-size:15px;">
        <div id="rec-amounts"></div>
        <div id="rec-sum" style="font-size:12px;margin-top:10px;"></div>
      </div>
      <div style="padding:14px 22px;border-top:1px solid var(--line,#eee);display:flex;gap:8px;justify-content:flex-end;">
        <button onclick="cerrarRecModal()" class="btn" style="background:#f1f5f9;color:#475569;">Cancelar</button>
        <button onclick="recGuardar(false)" class="btn" style="background:#ede9fe;color:#5b21b6;">Guardar</button>
        <button onclick="recGuardar(true)" class="btn btn-primary">&#128424;&#65039; Guardar e imprimir rótulos</button>
      </div>
    </div>
  </div>

</div>
<script>
var currentOC = null;
var _recCtx = null;      // {i, cod, lote, total} · contexto del modal de envases de la fila
var _envBreak = {};      // {rowIdx: [1000,1000,1000,500]} · desglose por envase guardado por fila
// Abre el modal de envases para la fila i · lee cantidad recibida + lote EN VIVO de la fila
function abrirRecModal(i){
  var btn = document.getElementById('env-btn-'+i);
  var cod = btn ? (btn.getAttribute('data-envcod')||'') : '';
  var cantEl = document.getElementById('cant-'+i);
  var total = parseFloat(cantEl ? cantEl.value : 0) || 0;
  if(total<=0){ alert('Poné primero la cantidad recibida de esta fila.'); return; }
  var loteEl = document.getElementById('lote-'+i);
  var lote = (loteEl ? loteEl.value : '').trim() || 'SL';
  _recCtx = {i:i, cod:cod, lote:lote, total:total};
  document.getElementById('rec-info').innerHTML = '<b>'+cod+'</b> &middot; lote '+lote+' &middot; total recibido <b>'+total.toLocaleString()+' g</b>';
  var prev = _envBreak[i];
  document.getElementById('rec-n').value = (prev && prev.length>1) ? prev.length : 1;
  recBuildInputs(prev);
  document.getElementById('rec-modal').style.display = 'flex';
}
function cerrarRecModal(){ var m=document.getElementById('rec-modal'); if(m) m.style.display='none'; _recCtx=null; }
function recBuildInputs(preAmts){
  if(!_recCtx) return;
  var n = Math.max(1, Math.min(60, parseInt(document.getElementById('rec-n').value)||1));
  var per = _recCtx.total>0 ? Math.round(_recCtx.total/n*100)/100 : 0;
  var usePrev = (preAmts && preAmts.length===n);
  var box = document.getElementById('rec-amounts');
  if(n<=1){ box.innerHTML='<div style="font-size:12px;color:var(--mut,#6b7280);">Un solo envase por '+_recCtx.total.toLocaleString()+' g (un rótulo).</div>'; document.getElementById('rec-sum').innerHTML=''; return; }
  var h='<div style="font-size:11px;color:var(--mut,#6b7280);margin-bottom:6px;">Cuánto hay en cada envase (ajustá si vienen desiguales, ej: 1000 / 1000 / 1000 / 500):</div><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:8px;">';
  for(var i=0;i<n;i++){
    var v = usePrev ? preAmts[i] : per;
    h+='<div><label style="font-size:10px;color:var(--mut,#6b7280);">Envase '+(i+1)+'</label><input type="number" class="rec-amt" min="0" step="0.01" value="'+v+'" oninput="recSum()" style="width:100%;padding:7px 9px;border:1px solid var(--line,#e5e7eb);border-radius:8px;font-size:13px;"></div>';
  }
  h+='</div>';
  box.innerHTML=h; recSum();
}
function _recAmts(){ return [].map.call(document.querySelectorAll('.rec-amt'), function(el){ return parseFloat(el.value)||0; }); }
function recSum(){
  if(!_recCtx) return;
  var amts=_recAmts();
  var el=document.getElementById('rec-sum');
  if(!amts.length){ el.innerHTML=''; return; }
  var sum=amts.reduce(function(a,b){return a+b;},0);
  var diff=Math.round((sum-_recCtx.total)*100)/100;
  el.innerHTML='Suma: <b>'+sum.toLocaleString()+' g</b> &middot; total recibido '+_recCtx.total.toLocaleString()+' g'+(Math.abs(diff)>0.01?' &middot; <span style="color:#c2410c;font-weight:700;">difiere '+diff+' g</span>':' &middot; <span style="color:#16a34a;font-weight:700;">cuadra &#10003;</span>');
}
// etiqueta compacta de la celda Envases segun el desglose guardado
function envCellLabel(amts){
  if(!amts || amts.length<=1) return '1 envase';
  if(amts.length<=4) return amts.length+' &middot; '+amts.map(function(v){return v.toLocaleString();}).join('+');
  return amts.length+' envases';
}
function _envGuardar(i){
  var amts=_recAmts().filter(function(v){ return v>0; });
  var btn=document.getElementById('env-btn-'+i);
  if(amts.length<=1){ delete _envBreak[i]; if(btn){ btn.innerHTML='1 envase'; btn.classList.remove('multi'); } }
  else{ _envBreak[i]=amts; if(btn){ btn.innerHTML=envCellLabel(amts); btn.classList.add('multi'); } }
  return amts;
}
// Guardar el desglose (y opcionalmente imprimir los rotulos por envase)
function recGuardar(alsoPrint){
  if(!_recCtx) return;
  var i=_recCtx.i;
  var amts=_envGuardar(i);
  if(alsoPrint){
    var loteEl=document.getElementById('lote-'+i);
    var lote=(loteEl?loteEl.value:'').trim();
    if(!lote){ alert('Poné primero el lote de esta fila para el rótulo.'); cerrarRecModal(); return; }
    var url='/rotulo-recepcion/'+encodeURIComponent(_recCtx.cod)+'/'+encodeURIComponent(lote)+'/'+encodeURIComponent(_recCtx.total||1);
    if(amts.length>1){ url+='?recs='+encodeURIComponent(amts.join(',')); }
    window.open(url,'_blank');
  }
  cerrarRecModal();
}

function renderQueue(all) {
  try {
    if (!Array.isArray(all)) all = [];
    // Pendientes = TODO lo que aun no esta totalmente recibido.
    // Incluye Autorizada, Pagada (en transito), Parcial y Aprobada.
    var pendientes = all.filter(function(x) {
      var sinRecibir = !x.fecha_recepcion || x.fecha_recepcion.length < 3;
      return (x.estado === 'Autorizada' && sinRecibir)
          || (x.estado === 'Pagada'     && sinRecibir)
          || (x.estado === 'Aprobada'   && sinRecibir)
          || x.estado === 'Parcial';
    });
    var el = document.getElementById('queue-list');
    if (pendientes.length === 0) {
      el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Sin OCs pendientes de recepcion.</p>';
      return;
    }
    var today = new Date();
    var html = '<div class="oc-queue">';
    pendientes.forEach(function(oc) {
      var dt = oc.fecha ? new Date(oc.fecha) : null;
      var dias = dt ? Math.floor((today - dt) / 86400000) : 0;
      // Badge segun estado real
      var badge = '';
      if (oc.en_transito) {
        badge = '<span style="display:inline-block;background:#1e40af;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;letter-spacing:.4px;">&#x1F69A; EN TR&Aacute;NSITO</span>';
      } else if (oc.estado === 'Parcial') {
        badge = '<span style="display:inline-block;background:#f59e0b;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;letter-spacing:.4px;">PARCIAL</span>';
      } else if (oc.estado === 'Aprobada') {
        badge = '<span style="display:inline-block;background:#9333ea;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;letter-spacing:.4px;">APROBADA</span>';
      }
      // Trazabilidad SOL → OC
      var solRef = oc.sol_numero
        ? '<div style="font-size:10px;color:#7c3aed;font-weight:600;margin-top:3px;">&larr; ' + oc.sol_numero + '</div>'
        : '';
      // ETA si la hay
      var eta = oc.fecha_entrega_est
        ? '<div style="font-size:10px;color:#0891b2;margin-top:2px;">&#x23F0; ETA ' + oc.fecha_entrega_est + '</div>'
        : '';
      // franja de estado (scan a la vista): azul=en tránsito · ámbar=parcial · violeta=aprobada
      var stripe = oc.en_transito ? '#3b82f6' : (oc.estado === 'Parcial' ? '#f59e0b' : (oc.estado === 'Aprobada' ? '#9333ea' : '#a78bfa'));
      html += '<div class="oc-card" data-oc="' + oc.numero_oc + '" style="border-left-color:' + stripe + ';" onclick="cargarOC(this.dataset.oc)">'
        + '<div style="display:flex;justify-content:space-between;align-items:start;gap:6px;">'
        +   '<div class="oc-num">' + oc.numero_oc + '</div>'
        +   badge
        + '</div>'
        + solRef
        + '<div class="oc-prov">' + (oc.proveedor || '') + '</div>'
        + '<div class="oc-val">$' + Number(oc.valor_total||0).toLocaleString() + '</div>'
        + eta
        + '<div class="oc-dias">' + (dias > 0 ? dias + 'd desde OC' : 'Reciente') + '</div>'
        + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  } catch(e) { console.error(e); }
}

function cargarOC(num) {
  document.getElementById('oc-input').value = num;
  buscarOC();
  document.getElementById('oc-section').scrollIntoView({behavior:'smooth'});
}

async function buscarOC() {
  var num = document.getElementById('oc-input').value.trim().toUpperCase();
  if (!num) return;
  showMsg('oc-msg', '', '');
  try {
    var r = await fetch('/api/recepcion/detalle/' + encodeURIComponent(num));
    var d = await r.json();
    if (!r.ok || d.error) {
      var msg = d.error || 'OC no encontrada';
      if (r.status === 422) msg = '⛔ ' + msg;
      showMsg('oc-msg', msg, 'err');
      document.getElementById('oc-section').style.display = 'none';
      return;
    }
    currentOC = d;
    renderOC(d);
    document.getElementById('oc-section').style.display = 'block';
  } catch(e) { showMsg('oc-msg', 'Error de red: ' + e.message, 'err'); }
}

function getItemIcon(est, pct) {
  if (est === 'OK' && pct >= 100) return '<span class="icon-ok">&#10003;</span>';
  if (est === 'Danado' || est === 'NoLlego') return '<span class="icon-falta">&#10007;</span>';
  if (pct < 100 || est !== 'OK') return '<span class="icon-disc">&#9888;</span>';
  return '';
}

function renderOC(d) {
  var badgeCls = 'badge-' + (d.estado||'').toLowerCase();
  document.getElementById('oc-header').innerHTML =
    '<div><div class="lbl">OC</div><div class="val">' + d.numero_oc + '</div></div>' +
    '<div><div class="lbl">Proveedor</div><div class="val">' + d.proveedor + '</div></div>' +
    '<div><div class="lbl">Fecha</div><div class="val">' + (d.fecha||'').slice(0,10) + '</div></div>' +
    '<div><div class="lbl">Estado</div><div class="val"><span class="badge ' + badgeCls + '">' + d.estado + '</span></div></div>' +
    '<div><div class="lbl">Valor Total</div><div class="val">$' + Number(d.valor_total||0).toLocaleString() + '</div></div>' +
    '<div><div class="lbl">Categoria</div><div class="val">' + (d.categoria||'MP') + '</div></div>';

  // Advertencia si OC ya fue procesada (static div in HTML, no DOM insertion needed)
  var warnEl = document.getElementById('oc-estado-warn');
  if (d.estado === 'Recibida' || d.estado === 'Pagada') {
    warnEl.style.background = '#fef9c3'; warnEl.style.color = '#854d0e'; warnEl.style.border = '1px solid #fde047'; warnEl.style.display = 'block';
    warnEl.textContent = '\u26a0 Esta OC ya fue recibida (' + d.estado + '). Puedes consultar pero el registro de recepcion esta completo.';
  } else if (d.estado === 'Rechazada') {
    warnEl.style.background = '#fee2e2'; warnEl.style.color = '#991b1b'; warnEl.style.border = '1px solid #fca5a5'; warnEl.style.display = 'block';
    warnEl.textContent = '\u274c Esta OC fue rechazada y no puede recibirse.';
  } else {
    warnEl.style.display = 'none'; warnEl.textContent = '';
  }
  var tbody = document.getElementById('items-body');
  tbody.innerHTML = '';
  _envBreak = {};   // limpiar desgloses de envases de la OC anterior (los índices de fila se reutilizan)
  var items = d.items || [];
  for (var idx = 0; idx < items.length; idx++) {
    (function(i, it) {
      var unidad = it.unidad || ((d.categoria === 'MEE') ? 'uds' : 'g');
      // Recepción parcial (Sebastián/Catalina 14-jul): pre-cargar lo PENDIENTE (no lo ya
      // recibido) y marcar como hechas las líneas completas → no doble-contar al re-abrir.
      var recibidoYa = Number(it.cantidad_recibida_g || 0);
      var pendiente = Math.max(0, Number(it.cantidad_g || 0) - recibidoYa);
      var yaCompleta = (recibidoYa > 0 && pendiente <= 0.01);
      var prevRec = yaCompleta ? recibidoYa : (pendiente > 0 ? pendiente : Number(it.cantidad_g || 0));
      var pct = it.cantidad_g > 0 ? Math.round(recibidoYa / it.cantidad_g * 100) : 100;
      var esMee = ((it.codigo_mp||'').toUpperCase().indexOf('MEE-') === 0) || (d.categoria === 'MEE');
      var tr = document.createElement('tr');
      tr.id = 'item-row-' + i;
      tr.innerHTML =
        '<td style="text-align:center;">' + getItemIcon('OK', pct) + '</td>' +
        '<td style="text-align:center;">' + (yaCompleta
            ? '<span title="Ya recibida completa" style="color:#16a34a;font-weight:800;font-size:15px;">&#10003;</span>'
            : '<input type="checkbox" id="rx-' + i + '" checked onchange="toggleRecibir(' + i + ')" style="width:18px;height:18px;cursor:pointer;" title="Destildá para dejar esta MP pendiente">') + '</td>' +
        '<td><strong>' + ((it.inci && it.inci.trim()) ? it.inci : it.codigo_mp) + '</strong><br><small style="color:#78716c">' + it.codigo_mp + (recibidoYa > 0 && !yaCompleta ? ' · <span style="color:#b45309;">ya recibido ' + recibidoYa.toLocaleString() + '</span>' : '') + '</small></td>' +
        '<td class="valor">' + Number(it.cantidad_g||0).toLocaleString() + ' ' + unidad + '</td>' +
        '<td><input type="number" id="cant-' + i + '" data-codigo="' + it.codigo_mp + '" data-sol="' + it.cantidad_g + '" value="' + prevRec + '"' + (yaCompleta ? ' disabled' : '') + ' min="0" step="0.01" oninput="updateRow(' + i + ')"></td>' +
        '<td id="dif-' + i + '" class="valor" style="font-weight:600;"></td>' +
        '<td><div class="progress-bar"><div class="progress-fill" id="prog-' + i + '" style="width:' + Math.min(pct,100) + '%"></div></div><div class="item-pct" id="pct-' + i + '">' + pct + '%</div></td>' +
        '<td><select id="est-' + i + '" onchange="updateRow(' + i + ')">' +
          '<option value="OK">OK - Conforme</option>' +
          '<option value="Incompleto">Incompleto</option>' +
          '<option value="Danado">Danado</option>' +
          '<option value="NoLlego">No llego</option>' +
        '</select></td>' +
        '<td><input type="text" id="lote-' + i + '" placeholder="Ej: L-2026-001" style="width:110px;"></td>' +
        '<td><input type="date" id="fv-' + i + '" style="width:130px;"></td>' +
        '<td><input type="text" id="nota-' + i + '" placeholder="Observacion opcional"></td>' +
        '<td style="text-align:center;">' + (esMee
            ? '<span style="color:#cbd5e1;font-size:12px;" title="Los envases (MEE) se cuentan en unidades, no aplica desglose en gramos">n/a</span>'
            : '<button type="button" class="btn-env" id="env-btn-' + i + '" onclick="abrirRecModal(' + i + ')" data-envcod="' + (it.codigo_mp||'') + '" title="Definir en cuántos envases llegó y cuánto hay en cada uno (ej: 3 de 1000 + 1 de 500)">1 envase</button>') + '</td>' +
        '<td style="text-align:center;"><button class="btn btn-print" style="padding:5px 11px;font-size:11px;white-space:nowrap;" data-rotidx="' + i + '" data-rotcod="' + (it.codigo_mp||'') + '" data-rotmee="' + (esMee ? 1 : 0) + '" title="Imprimir rótulo de este material (usa la cantidad recibida, el lote y el desglose de envases de esta fila)">&#128424;&#65039; Rótulo</button></td>';
      tbody.appendChild(tr);
      updateRow(i);
    })(idx, items[idx]);
  }
}

function filterByText(sel, q) {
  q = (q || '').trim().toLowerCase();
  var els = document.querySelectorAll(sel);
  for (var k = 0; k < els.length; k++) {
    var hit = !q || (els[k].textContent || '').toLowerCase().indexOf(q) >= 0;
    els[k].style.display = hit ? '' : 'none';
  }
}
function toggleRecibir(i) {
  var rx = document.getElementById('rx-' + i);
  var cant = document.getElementById('cant-' + i);
  var row = document.getElementById('item-row-' + i);
  if (cant) {
    var off = (rx && !rx.checked);
    cant.disabled = off;
    if (row) row.style.opacity = off ? '.5' : '1';
  }
  updateRow(i);
}
function updateRow(i) {
  var cantEl = document.getElementById('cant-' + i);
  var estEl = document.getElementById('est-' + i);
  var progEl = document.getElementById('prog-' + i);
  var pctEl = document.getElementById('pct-' + i);
  var difEl = document.getElementById('dif-' + i);
  var row = document.getElementById('item-row-' + i);
  if (!cantEl) return;
  var sol = parseFloat(cantEl.dataset.sol) || 0;
  var rec = parseFloat(cantEl.value) || 0;
  var est = estEl ? estEl.value : 'OK';
  var pct = sol > 0 ? Math.round(rec / sol * 100) : 100;
  var dif = rec - sol;
  if (difEl) {
    if (Math.abs(dif) < 0.001) { difEl.textContent = '\u2713'; difEl.style.color = '#16a34a'; }
    else if (dif < 0) { difEl.textContent = dif.toLocaleString(); difEl.style.color = '#dc2626'; }
    else { difEl.textContent = '+' + dif.toLocaleString(); difEl.style.color = '#d97706'; }
  }
  if (progEl) { progEl.style.width = Math.min(pct,100) + '%'; progEl.style.background = pct >= 100 ? '#16a34a' : pct > 50 ? '#d97706' : '#dc2626'; }
  if (pctEl) pctEl.textContent = pct + '%';
  if (row) { row.className = (est === 'OK' && pct >= 100) ? 'row-ok' : (est === 'Danado' || est === 'NoLlego' || pct === 0) ? 'row-falta' : 'row-disc'; }
}

async function registrarRecepcion() {
  if (!currentOC) return;
  var obs = document.getElementById('obs-input').value.trim();
  var receptor = document.getElementById('receptor-input').value.trim();
  if (!receptor) { showMsg('submit-msg', 'Ingresa quien recibe la mercancia', 'err'); return; }
  var items = [];
  var discrepancias = false;
  var ocItems = currentOC.items || [];
  for (var idx = 0; idx < ocItems.length; idx++) {
    var it = ocItems[idx];
    var cantEl = document.getElementById('cant-' + idx);
    var estEl = document.getElementById('est-' + idx);
    var notaEl = document.getElementById('nota-' + idx);
    // Recepción parcial: si la línea está destildada (o no tiene checkbox = ya recibida
    // completa), se manda 0 → el backend la salta y queda pendiente (no doble-cuenta).
    var rxEl = document.getElementById('rx-' + idx);
    var recibirEsta = rxEl ? rxEl.checked : false;
    var cant = (recibirEsta && cantEl) ? (parseFloat(cantEl.value) || 0) : 0;
    var est = estEl ? estEl.value : 'OK';
    var nota = notaEl ? notaEl.value.trim() : '';
    var loteEl = document.getElementById('lote-' + idx);
    var fvEl = document.getElementById('fv-' + idx);
    var lote = loteEl ? loteEl.value.trim() : '';
    var fv = fvEl ? fvEl.value.trim() : '';
    if (est !== 'OK' || cant < it.cantidad_g) discrepancias = true;
    var _amts = _envBreak[idx] || [];
    var nrec = _amts.length > 1 ? _amts.length : 1;
    items.push({codigo_mp: it.codigo_mp, cantidad_recibida: cant, estado: est, notas: nota, lote: lote, fecha_vencimiento: fv, recipientes: nrec, envases_detalle: (_amts.length > 1 ? _amts : null)});
  }
  var payload = {
    observaciones_recepcion: obs,
    tiene_discrepancias: discrepancias ? 1 : 0,
    items_recepcion: items,
    receptor_nombre: receptor,
    // idempotencia: token único por envío (evita doble Entrada por retry de red)
    recepcion_id: ((window.crypto && crypto.randomUUID) ? crypto.randomUUID()
                   : ('rcp-' + Date.now() + '-' + Math.random().toString(36).slice(2)))
  };
  showMsg('submit-msg', 'Registrando...', '');
  var _submitBtn = document.querySelector('.btn-success');
  if (_submitBtn) { _submitBtn.disabled = true; _submitBtn.textContent = 'Registrando...'; }
  try {
    var r = await fetch('/api/ordenes-compra/' + encodeURIComponent(currentOC.numero_oc) + '/recibir', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    var d = await r.json();
    if (d.ok) {
      var discMsg = discrepancias ? ' \u26a0 Con discrepancias.' : '';
      var parcialMsg = d.parcial ? ' \u26a1 Recepcion PARCIAL - OC sigue abierta para completar.' : '';
      showMsg('submit-msg', 'Recepcion registrada. ' + (d.ingresos||0) + ' item(s) ingresado(s).' + discMsg + parcialMsg, 'ok');
      var submitRow = document.querySelector('.submit-row');
      if (submitRow) {
        var printBtn = document.createElement('button');
        printBtn.className = 'btn btn-print';
        printBtn.textContent = '🖨 Imprimir Acta de Recepcion';
        printBtn.onclick = function() { imprimirActaRecepcion(currentOC, payload, d); };
        submitRow.appendChild(printBtn);
      }
      document.getElementById('oc-section').style.display = 'none';
      currentOC = null;
      document.getElementById('oc-input').value = '';
      document.getElementById('receptor-input').value = '';
      document.getElementById('obs-input').value = '';
      if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; }
      loadSeguimiento();
    } else {
      showMsg('submit-msg', d.error || 'Error al registrar', 'err');
      if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; }
    }
  } catch(e) { showMsg('submit-msg', 'Error de red: ' + e.message, 'err'); if (_submitBtn) { _submitBtn.disabled = false; _submitBtn.textContent = '\u2713 Registrar Recepcion'; } }
}

function imprimirActaRecepcion(oc, payload, result) {
  var w = window.open('', '_blank', 'width=760,height=900,toolbar=0,scrollbars=1,resizable=1');
  var hoy = new Date().toLocaleString('es-CO');
  var itemsHtml = (payload.items_recepcion || []).map(function(it) {
    var cls = it.estado === 'OK' ? 'color:#16a34a' : 'color:#dc2626';
    return '<tr><td>' + it.codigo_mp + '</td><td>' + it.cantidad_recibida.toLocaleString() + '</td><td style="' + cls + ';font-weight:600;">' + it.estado + '</td><td>' + (it.notas||'-') + '</td></tr>';
  }).join('');
  var discBanner = payload.tiene_discrepancias
    ? '<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:12px;margin-bottom:16px;color:#92400e;font-weight:600;">⚠ Esta recepcion contiene discrepancias. Requiere revision.</div>'
    : '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:12px;margin-bottom:16px;color:#166534;font-weight:600;">✓ Recepcion conforme sin discrepancias.</div>';
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Acta Recepcion</title>'
    + '<style>body{font-family:Arial,sans-serif;padding:30px;font-size:13px;color:#1C1917;}'
    + 'h2{color:#292524;margin-bottom:4px;}h3{color:#57534e;margin:20px 0 10px;}'
    + '.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;}'
    + 'table{width:100%;border-collapse:collapse;margin-bottom:16px;}'
    + 'th{background:#f5f5f4;padding:8px 10px;text-align:left;font-size:11px;color:#57534e;border:1px solid #e7e5e4;}'
    + 'td{padding:7px 10px;border:1px solid #e7e5e4;}'
    + '.meta{background:#fafaf9;border-radius:6px;padding:14px;margin-bottom:16px;display:grid;grid-template-columns:1fr 1fr;gap:8px;}'
    + '.meta .lbl{font-size:10px;color:#78716c;text-transform:uppercase;} .meta .val{font-size:13px;font-weight:600;}'
    + '.firma{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:40px;}'
    + '.firma-box{border-top:1px solid #292524;padding-top:8px;font-size:11px;color:#78716c;text-align:center;}'
    + '.noPrint{text-align:center;margin-bottom:20px;} @media print{.noPrint{display:none!important;}}'
    + '</style></head><body>'
    + '<div class="noPrint"><button onclick="window.print()" style="padding:9px 24px;background:#292524;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;">Imprimir</button></div>'
    + '<div class="header"><div><h2>ACTA DE RECEPCION DE MERCANCIA</h2><p style="color:#78716c;font-size:12px;">Espagiria Laboratorio - COC-PRO-002-F07</p></div>'
    + '<div style="text-align:right;font-size:11px;color:#78716c;"><div>Fecha: ' + hoy + '</div></div></div>'
    + discBanner
    + '<div class="meta">'
    + '<div><div class="lbl">No. OC</div><div class="val">' + (oc ? oc.numero_oc : '-') + '</div></div>'
    + '<div><div class="lbl">Proveedor</div><div class="val">' + (oc ? oc.proveedor : '-') + '</div></div>'
    + '<div><div class="lbl">Categoria</div><div class="val">' + (oc ? (oc.categoria||'MP') : '-') + '</div></div>'
    + '<div><div class="lbl">Valor Total OC</div><div class="val">$' + Number((oc ? oc.valor_total : 0)||0).toLocaleString() + '</div></div>'
    + '</div>'
    + '<h3>Detalle de items recibidos</h3>'
    + '<table><thead><tr><th>Codigo MP</th><th>Cant. Recibida</th><th>Estado</th><th>Notas</th></tr></thead><tbody>' + itemsHtml + '</tbody></table>'
    + '<h3>Observaciones</h3>'
    + '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:6px;padding:12px;min-height:60px;">' + (payload.observaciones_recepcion||'Sin observaciones adicionales.') + '</div>'
    + '<div class="firma">'
    + '<div class="firma-box">Recibido por<br><br><strong>' + payload.receptor_nombre + '</strong></div>'
    + '<div class="firma-box">Control de Calidad<br><br>&nbsp;</div>'
    + '</div>'
    + '</body></html>');
  w.document.close();
}

function showMsg(id, text, type) {
  var el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = 'msg' + (type==='ok' ? ' msg-ok' : type==='err' ? ' msg-err' : '');
  el.style.display = text ? 'block' : 'none';
}

function showTab(name) {
  ['transito','parcial','recibidas','disc'].forEach(function(t) {
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
    document.getElementById('tab-btn-' + t).classList.toggle('active', t === name);
  });
}

function fmtDate(s) { return s ? String(s).slice(0,10) : '-'; }
function fmtVal(v) { return '$' + Number(v||0).toLocaleString(); }

function buildTable(rows) {
  if (!rows.length) return '<div class="empty">Sin registros</div>';
  var h = '<div style="overflow-x:auto"><table><thead><tr>'
    + '<th>OC</th><th>Proveedor</th><th>Cat.</th><th>Valor</th>'
    + '<th>Fecha OC</th><th>F. Aut.</th><th>F. Pago</th><th>F. Recepcion</th><th>Recibido Por</th><th>Observaciones</th>'
    + '</tr></thead><tbody>';
  rows.forEach(function(row) {
    var disc = row.tiene_discrepancias ? '<span class="disc"> &#9888; DISC</span>' : '';
    h += '<tr><td><strong>' + row.numero_oc + '</strong>' + disc + '</td>'
      + '<td>' + row.proveedor + '</td><td>' + row.categoria + '</td>'
      + '<td class="valor">' + fmtVal(row.valor_total) + '</td>'
      + '<td>' + fmtDate(row.fecha) + '</td>'
      + '<td>' + fmtDate(row.fecha_autorizacion) + '</td>'
      + '<td>' + fmtDate(row.fecha_pago) + '</td>'
      + '<td>' + (row.fecha_recepcion ? fmtDate(row.fecha_recepcion) : '<span style="color:#d97706">Pendiente</span>') + '</td>'
      + '<td style="color:#57534e">' + (row.recibido_por||'-') + '</td>'
      + '<td style="max-width:200px;color:#57534e">' + (row.observaciones||'-') + '</td>'
      + '</tr>';
  });
  h += '</tbody></table></div>';
  return h;
}

function renderMonitoreo(all) {
  try {
    if (!Array.isArray(all)) all = [];
    var transito = all.filter(function(x) { return x.estado === 'Autorizada' && (!x.fecha_recepcion || x.fecha_recepcion.length < 3); });
    var parcial = all.filter(function(x) { return x.estado === 'Parcial'; });
    var recibidas = all.filter(function(x) { return (x.estado === 'Recibida' || x.estado === 'Pagada') && x.fecha_recepcion && x.fecha_recepcion.length > 2; });
    var disc = all.filter(function(x) { return x.tiene_discrepancias; });
    document.getElementById('cnt-transito').textContent = transito.length;
    document.getElementById('cnt-parcial').textContent = parcial.length;
    document.getElementById('cnt-recibidas').textContent = recibidas.length;
    document.getElementById('cnt-disc').textContent = disc.length;
    document.getElementById('tab-transito').innerHTML = buildTable(transito);
    document.getElementById('tab-parcial').innerHTML = buildTable(parcial);
    document.getElementById('tab-recibidas').innerHTML = buildTable(recibidas);
    document.getElementById('tab-disc').innerHTML = buildTable(disc);
  } catch(e) { console.error(e); }
}

// Imprimir rótulo · ítems de Registrar Recepción (lee cantidad + lote EN VIVO de la fila)
document.addEventListener('click', function(e) {
  var b = e.target.closest('[data-rotidx]');
  if (!b) return;
  var i = b.getAttribute('data-rotidx');
  var cod = b.getAttribute('data-rotcod') || '';
  var esMee = b.getAttribute('data-rotmee') === '1';
  var cantEl = document.getElementById('cant-' + i);
  var cant = parseFloat(cantEl ? cantEl.value : 0) || 0;
  if (cant <= 0) { alert('Poné primero la cantidad recibida de esta fila.'); return; }
  if (esMee) {
    window.open('/rotulo-recepcion-mee/' + encodeURIComponent(cod) + '/' + cant, '_blank');
  } else {
    var loteEl = document.getElementById('lote-' + i);
    var lote = (loteEl ? loteEl.value : '').trim();
    if (!lote) { alert('Poné primero el lote de esta fila para el rótulo.'); return; }
    // MP: imprime usando el desglose de envases guardado en la fila (1 rótulo por envase con SU
    // cantidad · Laura 16-jul). Si no se definió, sale un rótulo por la cantidad total.
    var amts = _envBreak[i] || [];
    var url = '/rotulo-recepcion/' + encodeURIComponent(cod) + '/' + encodeURIComponent(lote) + '/' + encodeURIComponent(cant || 1);
    if (amts.length > 1) { url += '?recs=' + encodeURIComponent(amts.join(',')); }
    window.open(url, '_blank');
  }
});



async function buscarLote() {
  var lote = document.getElementById('lote-input').value.trim();
  if (!lote) return;
  var el = document.getElementById('lote-result');
  el.innerHTML = '<p style="color:#a8a29e;font-size:13px;">Buscando...</p>';
  try {
    var r = await fetch('/api/recepcion/trazabilidad/' + encodeURIComponent(lote));
    var d = await r.json();
    var movs = d.movimientos || [];
    if (!movs.length) { el.innerHTML = '<p style="color:#dc2626;font-size:13px;">Lote no encontrado.</p>'; return; }
    var oc = d.oc;
    var h = '';
    if (oc) {
      h += '<div style="background:#fafaf9;border:1px solid #e7e5e4;border-radius:8px;padding:12px;margin-bottom:12px;">'
        + '<div style="font-weight:700;margin-bottom:6px;">OC de Origen: ' + oc.numero_oc + '</div>'
        + '<div style="font-size:12px;color:#57534e;">Proveedor: ' + (oc.proveedor||'-') + ' | Fecha: ' + (oc.fecha||'-').slice(0,10) + ' | Estado OC: ' + (oc.estado||'-') + ' | Recibido por: ' + (oc.recibido_por||'-') + '</div>'
        + '</div>';
    }
    h += '<table><thead><tr><th>Material</th><th>Cant.</th><th>Tipo</th><th>Fecha</th><th>Estado Lote</th><th>Proveedor</th><th>Vence</th></tr></thead><tbody>';
    movs.forEach(function(m) {
      // H1 (12-jun): el estado_lote ahora es canonico MAYUSCULAS (VIGENTE/RECHAZADO/
      // CUARENTENA · M23). Antes comparaba 'Aprobado'/'Rechazado' (Title) -> nunca
      // matcheaba -> TODO salia ambar (un RECHAZADO se veia ambar, no rojo).
      var _est = (m.estado_lote||'').toUpperCase();
      var estadoColor = (_est === 'VIGENTE' || _est === 'APROBADO') ? '#16a34a' : _est === 'RECHAZADO' ? '#dc2626' : '#d97706';
      h += '<tr><td><strong>' + (m.material_nombre||m.material_id||'') + '</strong></td>'
        + '<td>' + Number(m.cantidad||0).toLocaleString() + '</td>'
        + '<td>' + (m.cantidad > 0 ? 'Entrada' : 'Salida') + '</td>'
        + '<td>' + (m.fecha||'-').slice(0,10) + '</td>'
        + '<td style="color:' + estadoColor + ';font-weight:600;">' + (m.estado_lote||'Sin estado') + '</td>'
        + '<td>' + (m.proveedor||'-') + '</td>'
        + '<td>' + (m.fecha_vencimiento||'-').slice(0,10) + '</td>'
        + '</tr>';
    });
    h += '</tbody></table>';
    el.innerHTML = h;
  } catch(e) { el.innerHTML = '<p style="color:#dc2626;">Error: ' + e.message + '</p>'; }
}

// PERF (Sebastián 15-jul): loadQueue y loadMonitoreo pedían el MISMO endpoint
// /api/recepcion/seguimiento (doble llamada pesada en el load · M43/M59). Ahora UN
// solo fetch y se comparte el array entre las dos vistas.
async function loadSeguimiento() {
  try {
    var r = await fetch('/api/recepcion/seguimiento');
    var all = await r.json();
    if (!Array.isArray(all)) all = [];
    renderQueue(all);
    renderMonitoreo(all);
  } catch(e) {
    console.error(e);
    renderQueue([]); renderMonitoreo([]);
  }
}
loadSeguimiento();
</script>
</body>
</html>
"""

