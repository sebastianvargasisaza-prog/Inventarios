# calidad_html.py — extraído de index.py (Fase C prep)
CALIDAD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Calidad BPM — Espagiria</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;font-size:14px;min-height:100vh;}
.topbar{background:#1e293b;border-bottom:1px solid #334155;padding:12px 24px;display:flex;align-items:center;gap:16px;}
.logo{font-size:0.85em;font-weight:900;letter-spacing:3px;color:#fff;}
.badge{background:rgba(43,122,120,0.4);color:#7ACFCC;padding:3px 12px;border-radius:20px;font-size:0.7em;font-weight:700;letter-spacing:1px;}
.topbar a{color:rgba(255,255,255,0.45);text-decoration:none;font-size:0.78em;padding:5px 12px;border:1px solid rgba(255,255,255,0.12);border-radius:6px;margin-left:auto;}
.topbar a:hover{color:#fff;border-color:rgba(255,255,255,0.35);}
.tabs{display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;padding:0 24px;}
.tab{padding:11px 20px;font-size:0.78em;font-weight:700;letter-spacing:.5px;color:#64748b;cursor:pointer;border-bottom:2px solid transparent;text-transform:uppercase;}
.tab.active{color:#7ACFCC;border-bottom-color:#7ACFCC;}
.tab:hover{color:#cbd5e1;}
.main{padding:24px;max-width:1300px;margin:0 auto;}
.kpi-row{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px;}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px 20px;flex:1;min-width:140px;}
.kpi-label{font-size:0.68em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:6px;}
.kpi-val{font-size:2em;font-weight:800;color:#f1f5f9;}
.kpi-val.warn{color:#fb923c;}
.kpi-val.crit{color:#f87171;}
.kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:0.7em;color:#475569;margin-top:3px;}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:18px;margin-bottom:16px;}
.card-title{font-size:0.7em;text-transform:uppercase;letter-spacing:1.5px;color:#64748b;margin-bottom:14px;font-weight:700;}
table{width:100%;border-collapse:collapse;}
th{font-size:0.67em;text-transform:uppercase;letter-spacing:.8px;color:#475569;padding:8px 10px;text-align:left;border-bottom:1px solid #334155;}
td{padding:9px 10px;font-size:0.82em;border-bottom:1px solid #1e293b;color:#cbd5e1;vertical-align:top;}
tr:hover td{background:#0f172a;}
.badge-verde{background:#052e16;color:#4ade80;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-amarillo{background:#451a03;color:#fcd34d;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-rojo{background:#450a0a;color:#fca5a5;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;}
.badge-gris{background:#1e293b;color:#94a3b8;padding:2px 10px;border-radius:20px;font-size:0.72em;font-weight:700;border:1px solid #334155;}
.btn{padding:7px 16px;border-radius:7px;border:none;font-size:0.78em;font-weight:700;cursor:pointer;letter-spacing:.3px;}
.btn-primary{background:#2B7A78;color:#fff;}
.btn-primary:hover{background:#1e5c5a;}
.btn-danger{background:#7f1d1d;color:#fca5a5;}
.btn-danger:hover{background:#991b1b;}
.btn-sm{padding:4px 10px;font-size:0.72em;}
.form-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px;align-items:flex-end;}
.form-group{display:flex;flex-direction:column;gap:4px;flex:1;min-width:160px;}
label{font-size:0.7em;text-transform:uppercase;letter-spacing:.8px;color:#64748b;font-weight:700;}
input,select,textarea{background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:7px 10px;border-radius:7px;font-size:0.82em;width:100%;}
input:focus,select:focus,textarea:focus{outline:none;border-color:#7ACFCC;}
textarea{resize:vertical;min-height:70px;}
.pane{display:none;} .pane.active{display:block;}
.empty{color:#475569;text-align:center;padding:32px;font-size:0.85em;}
.actividad{display:flex;flex-direction:column;gap:8px;}
.act-item{background:#0f172a;border-radius:8px;padding:10px 14px;border:1px solid #1e293b;display:flex;align-items:flex-start;gap:10px;}
.act-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px;}
.dot-verde{background:#4ade80;} .dot-rojo{background:#f87171;} .dot-amari{background:#fcd34d;}
.act-body{flex:1;}
.act-title{font-size:0.78em;font-weight:700;color:#e2e8f0;}
.act-sub{font-size:0.68em;color:#64748b;margin-top:1px;}
.alert-box{background:#450a0a;border:1px solid #7f1d1d;border-radius:8px;padding:10px 14px;margin-bottom:12px;color:#fca5a5;font-size:0.8em;}
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">ESPAGIRIA</span>
  <span class="badge">CALIDAD BPM</span>
  <a href="/">&#8592; Inicio</a>
</div>
<div class="tabs">
  <div class="tab active" onclick="goTab('tab-dash')">Dashboard</div>
  <div class="tab" onclick="goTab('tab-cc')">&#x1F9EA; Control Calidad MP</div>
  <div class="tab" onclick="goTab('tab-nc')">&#x26A0; No Conformidades</div>
  <div class="tab" onclick="goTab('tab-cal')">&#x1F527; Calibraciones</div>
</div>
<div class="main">

<!-- ── DASHBOARD ─────────────────────────────────────── -->
<div id="tab-dash" class="pane active">
  <div class="kpi-row">
    <div class="kpi"><div class="kpi-label">Lotes en Cuarentena</div><div class="kpi-val warn" id="kv-cuarentena">—</div><div class="kpi-sub">Pendientes CC</div></div>
    <div class="kpi"><div class="kpi-label">Aprobados (30d)</div><div class="kpi-val good" id="kv-aprobados">—</div><div class="kpi-sub">Lotes aprobados</div></div>
    <div class="kpi"><div class="kpi-label">Rechazados (30d)</div><div class="kpi-val crit" id="kv-rechazados">—</div><div class="kpi-sub">Lotes rechazados</div></div>
    <div class="kpi"><div class="kpi-label">NC Abiertas</div><div class="kpi-val warn" id="kv-nc">—</div><div class="kpi-sub">No conformidades</div></div>
    <div class="kpi"><div class="kpi-label">Calibraciones Vencidas</div><div class="kpi-val crit" id="kv-cals">—</div><div class="kpi-sub">Requieren accion</div></div>
  </div>
  <div class="card">
    <div class="card-title">Actividad Reciente</div>
    <div class="actividad" id="act-list"><p class="empty">Cargando...</p></div>
  </div>
</div>

<!-- ── CONTROL CALIDAD MP (cuarentena) ───────────────── -->
<div id="tab-cc" class="pane">
  <div class="card">
    <div class="card-title">Lotes en Cuarentena — Pendientes de Revision</div>
    <table>
      <thead><tr><th>MP / Lote</th><th>Cantidad</th><th>Proveedor</th><th>Fec. Vencimiento</th><th>OC</th><th>Accion</th></tr></thead>
      <tbody id="cc-tbody"><tr><td colspan="6" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ── NO CONFORMIDADES ─────────────────────────────── -->
<div id="tab-nc" class="pane">
  <div class="card">
    <div class="card-title">Registrar No Conformidad</div>
    <div class="form-row">
      <div class="form-group"><label>Tipo</label><select id="nc-tipo"><option>Proceso</option><option>Producto</option><option>Proveedor</option><option>Equipo</option><option>Documentacion</option></select></div>
      <div class="form-group"><label>Area</label><select id="nc-area"><option>Produccion</option><option>Laboratorio</option><option>Calidad</option><option>Administrativa</option><option>Almacen</option></select></div>
      <div class="form-group"><label>Impacto</label><select id="nc-impacto"><option>Bajo</option><option>Medio</option><option>Alto</option><option>Critico</option></select></div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:2"><label>Descripcion</label><textarea id="nc-desc" placeholder="Describir la no conformidad detectada..."></textarea></div>
      <div class="form-group"><label>Responsable</label><input id="nc-responsable" placeholder="Nombre responsable"/></div>
    </div>
    <div class="form-row">
      <div class="form-group"><label>Lote (si aplica)</label><input id="nc-lote" placeholder="Ej: LOT-001"/></div>
      <div class="form-group"><label>Codigo MP (si aplica)</label><input id="nc-mp" placeholder="Ej: MPMP00001"/></div>
      <div class="form-group"><label>Accion Correctiva</label><textarea id="nc-accion" placeholder="Accion inmediata tomada..." style="min-height:50px"></textarea></div>
    </div>
    <button class="btn btn-primary" onclick="registrarNC()">Registrar NC</button>
  </div>
  <div class="card">
    <div class="card-title">Historial de No Conformidades</div>
    <table>
      <thead><tr><th>ID</th><th>Fecha</th><th>Tipo</th><th>Area</th><th>Descripcion</th><th>Impacto</th><th>Estado</th><th>Accion</th></tr></thead>
      <tbody id="nc-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- ── CALIBRACIONES ────────────────────────────────── -->
<div id="tab-cal" class="pane">
  <div class="card">
    <div class="card-title">Instrumentos y Equipos — Estado de Calibracion</div>
    <table>
      <thead><tr><th>Instrumento</th><th>Codigo</th><th>Ubicacion</th><th>Ultima Cal.</th><th>Proxima Cal.</th><th>Responsable</th><th>Certificado</th><th>Estado</th></tr></thead>
      <tbody id="cal-tbody"><tr><td colspan="8" class="empty">Cargando...</td></tr></tbody>
    </table>
  </div>
</div>

</div><!-- /main -->

<script>
function esc(s){const d=document.createElement('div');d.appendChild(document.createTextNode(s||''));return d.innerHTML;}
function fmt(d){return d?d.substring(0,10):'—';}

function goTab(id){
  document.querySelectorAll('.tab').forEach((t,i)=>{
    const ids=['tab-dash','tab-cc','tab-nc','tab-cal'];
    t.classList.toggle('active',ids[i]===id);
  });
  document.querySelectorAll('.pane').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if(id==='tab-dash') loadDash();
  else if(id==='tab-cc') loadCuarentena();
  else if(id==='tab-nc') loadNC();
  else if(id==='tab-cal') loadCal();
}

async function loadDash(){
  try{
    const r=await fetch('/api/calidad/dashboard');
    const d=await r.json();
    document.getElementById('kv-cuarentena').textContent=d.cuarentena||0;
    document.getElementById('kv-aprobados').textContent=d.aprobados||0;
    document.getElementById('kv-rechazados').textContent=d.rechazados||0;
    document.getElementById('kv-nc').textContent=d.nc_abiertas||0;
    document.getElementById('kv-cals').textContent=d.cals_vencidas||0;
    const act=document.getElementById('act-list');
    const items=(d.actividad_reciente||[]);
    if(!items.length){act.innerHTML='<p class="empty">Sin actividad reciente</p>';return;}
    act.innerHTML=items.map(a=>`
      <div class="act-item">
        <div class="act-dot dot-${a.color||'verde'}"></div>
        <div class="act-body">
          <div class="act-title">${esc(a.titulo)}</div>
          <div class="act-sub">${esc(a.subtitulo||'')} ${a.fecha?'&middot; '+fmt(a.fecha):''}</div>
        </div>
      </div>`).join('');
  }catch(e){document.getElementById('act-list').innerHTML='<p class="empty">Error: '+esc(e.message)+'</p>';}
}

async function loadCuarentena(){
  const tbody=document.getElementById('cc-tbody');
  try{
    const r=await fetch('/api/recepcion/lotes-cuarentena');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="6" class="empty">No hay lotes en cuarentena</td></tr>';return;}
    tbody.innerHTML=rows.map(l=>`<tr>
      <td><strong>${esc(l.material_nombre)}</strong><br><small style="color:#64748b">${esc(l.lote||'sin lote')}</small></td>
      <td>${esc(String(l.cantidad))} g</td>
      <td>${esc(l.proveedor||'—')}</td>
      <td>${fmt(l.fecha_vencimiento)}</td>
      <td>${esc(l.numero_oc||'—')}</td>
      <td style="display:flex;gap:6px">
        <button class="btn btn-primary btn-sm" data-aprobar="${l.id}" data-estado="Aprobado">Aprobar</button>
        <button class="btn btn-danger btn-sm" data-aprobar="${l.id}" data-estado="Rechazado">Rechazar</button>
      </td>
    </tr>`).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="6" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(e){
  const btn=e.target.closest('[data-aprobar]');
  if(!btn) return;
  const movId=btn.dataset.aprobar;
  const estado=btn.dataset.estado;
  if(!confirm('Confirmar: '+estado+' este lote?')) return;
  try{
    const r=await fetch('/api/recepcion/aprobar-lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mov_id:movId,estado})});
    if(r.ok) loadCuarentena();
    else alert('Error al actualizar');
  }catch(e){alert('Error: '+e.message);}
});

async function registrarNC(){
  const desc=document.getElementById('nc-desc').value.trim();
  if(!desc){alert('La descripcion es obligatoria');return;}
  const body={
    tipo:document.getElementById('nc-tipo').value,
    area:document.getElementById('nc-area').value,
    impacto:document.getElementById('nc-impacto').value,
    descripcion:desc,
    responsable:document.getElementById('nc-responsable').value,
    lote:document.getElementById('nc-lote').value,
    codigo_mp:document.getElementById('nc-mp').value,
    accion_correctiva:document.getElementById('nc-accion').value
  };
  try{
    const r=await fetch('/api/calidad/no-conformidades',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(r.ok){
      ['nc-desc','nc-responsable','nc-lote','nc-mp','nc-accion'].forEach(id=>document.getElementById(id).value='');
      loadNC();
    } else {const d=await r.json();alert(d.error||'Error al registrar');}
  }catch(e){alert('Error: '+e.message);}
}

async function loadNC(){
  const tbody=document.getElementById('nc-tbody');
  try{
    const r=await fetch('/api/calidad/no-conformidades');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay no conformidades registradas</td></tr>';return;}
    tbody.innerHTML=rows.map(nc=>{
      const bestado=nc.estado==='Abierta'?'badge-amarillo':(nc.estado==='Cerrada'?'badge-verde':'badge-gris');
      const bimpacto=nc.impacto==='Critico'?'badge-rojo':(nc.impacto==='Alto'?'badge-amarillo':'badge-gris');
      return `<tr>
        <td>#${nc.id}</td>
        <td>${fmt(nc.fecha)}</td>
        <td>${esc(nc.tipo)}</td>
        <td>${esc(nc.area)}</td>
        <td>${esc(nc.descripcion)}</td>
        <td><span class="${bimpacto}">${esc(nc.impacto)}</span></td>
        <td><span class="${bestado}">${esc(nc.estado)}</span></td>
        <td>${nc.estado==='Abierta'?`<button class="btn btn-sm btn-primary" data-cerrar-nc="${nc.id}">Cerrar</button>`:'—'}</td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

document.addEventListener('click',async function(ev){
  const btn=ev.target.closest('[data-cerrar-nc]');
  if(!btn) return;
  const ncid=btn.dataset.cerrarNc;
  if(!confirm('Cerrar esta no conformidad?')) return;
  try{
    const r=await fetch('/api/calidad/no-conformidades/'+ncid+'/cerrar',{method:'POST'});
    if(r.ok) loadNC();
    else alert('Error al cerrar NC');
  }catch(e){alert('Error: '+e.message);}
});

async function loadCal(){
  const tbody=document.getElementById('cal-tbody');
  try{
    const r=await fetch('/api/calidad/calibraciones');
    const rows=await r.json();
    if(!rows.length){tbody.innerHTML='<tr><td colspan="8" class="empty">No hay instrumentos registrados</td></tr>';return;}
    tbody.innerHTML=rows.map(c=>{
      const bs=c.estado==='Vigente'?'badge-verde':(c.estado==='Vencida'?'badge-rojo':'badge-amarillo');
      const hoy=new Date().toISOString().substring(0,10);
      const vence=c.fecha_proxima&&c.fecha_proxima<hoy;
      return `<tr>
        <td><strong>${esc(c.instrumento)}</strong></td>
        <td>${esc(c.codigo)}</td>
        <td>${esc(c.ubicacion)}</td>
        <td>${fmt(c.fecha_ultima)}</td>
        <td style="${vence?'color:#f87171;font-weight:700':''}">${fmt(c.fecha_proxima)}</td>
        <td>${esc(c.responsable)}</td>
        <td><small style="color:#64748b">${esc(c.certificado||'—')}</small></td>
        <td><span class="${bs}">${esc(c.estado)}</span></td>
      </tr>`;
    }).join('');
  }catch(e){tbody.innerHTML='<tr><td colspan="8" class="empty">Error: '+esc(e.message)+'</td></tr>';}
}

loadDash();
</script>
</body>
</html>"""

