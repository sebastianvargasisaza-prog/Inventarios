# Auto-extraído de index.py - Fase A refactor
HUB_HTML = """<!DOCTYPE html>
<html lang="es" translate="no">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>EOS · Panel Central</title>
<link rel="stylesheet" href="/static/cortex.css?v=eos15">
<script>(function(){try{var t=localStorage.getItem("cx-theme");if(t==="dark")document.documentElement.setAttribute("data-theme","dark");}catch(e){}})();</script>
<meta name="application-name" content="EOS">
<meta name="apple-mobile-web-app-title" content="EOS">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#6d28d9">
<meta name="description" content="EOS · Todo el holding, al frente · Desarrollado por HHA Group">
<meta name="author" content="HHA Group">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',sans-serif;background:var(--cx-text);color:var(--cx-border);font-size:14px;min-height:100vh;}
.header{background:var(--cx-text);border-bottom:1px solid var(--cx-text-soft);padding:14px 20px;display:flex;align-items:center;gap:12px;}
.header-logo{font-size:20px;font-weight:800;color:#fff;letter-spacing:-0.5px;}
.header-sub{font-size:12px;color:var(--cx-text-faint);margin-top:1px;}
.header-right{margin-left:auto;text-align:right;font-size:12px;color:var(--cx-text-faint);}
.header-right strong{display:block;color:#fff;font-size:13px;}
.alert-bar{padding:10px 20px;display:flex;gap:10px;align-items:center;background:var(--cx-text);border-bottom:1px solid var(--cx-text-soft);flex-wrap:wrap;}
.al-pill{display:flex;align-items:center;gap:5px;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:700;cursor:pointer;}
.al-crit{background:#450a0a;color:#fca5a5;border:1px solid var(--cx-danger);}
.al-aten{background:#451a03;color:#fcd34d;border:1px solid var(--cx-accent-dark);}
.al-ok{background:#052e16;color:#86efac;border:1px solid #14532d;}
.al-pulse{width:8px;height:8px;border-radius:50%;animation:pulse 1.5s infinite;}
.al-crit .al-pulse{background:var(--cx-danger);}
.al-aten .al-pulse{background:var(--cx-warn);}
.al-ok .al-pulse{background:#22c55e;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
.main{padding:20px;max-width:1400px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:768px){.main{grid-template-columns:1fr;}}
.card{background:var(--cx-text);border:1px solid var(--cx-text-soft);border-radius:10px;padding:16px;}
.card-title{font-size:12px;font-weight:700;color:var(--cx-text-faint);text-transform:uppercase;letter-spacing:.7px;margin-bottom:12px;display:flex;align-items:center;gap:6px;}
.card-full{grid-column:1/-1;}
.alert-item{display:flex;align-items:flex-start;gap:10px;padding:10px;border-radius:8px;margin-bottom:8px;background:var(--cx-text);border:1px solid var(--cx-text);}
.alert-item.crit{border-left:3px solid var(--cx-danger);}
.alert-item.aten{border-left:3px solid var(--cx-warn);}
.al-icon{font-size:16px;flex-shrink:0;margin-top:1px;}
.al-body{flex:1;}
.al-title{font-size:12px;font-weight:700;color:var(--cx-border);margin-bottom:2px;}
.al-detail{font-size:11px;color:var(--cx-text-faint);line-height:1.4;}
.al-action{display:inline-block;margin-top:5px;padding:3px 10px;background:var(--cx-text-soft);color:var(--cx-border);border-radius:4px;font-size:10px;text-decoration:none;font-weight:600;}
.al-action:hover{background:var(--cx-text-soft);}
.kpi-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;}
.kpi{background:var(--cx-text);border:1px solid var(--cx-text-soft);border-radius:8px;padding:12px;}
.kpi-label{font-size:10px;color:var(--cx-text-mute);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;}
.kpi-val{font-size:22px;font-weight:800;color:var(--cx-border-soft);}
.kpi-val.warn{color:#fb923c;}
.kpi-val.crit{color:#f87171;}
.kpi-val.good{color:#4ade80;}
.kpi-sub{font-size:11px;color:var(--cx-text-mute);margin-top:2px;}
.module-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;}
.mod-btn{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 10px;background:var(--cx-text);border:1px solid var(--cx-text-soft);border-radius:10px;text-decoration:none;color:var(--cx-border);transition:.15s;cursor:pointer;}
.mod-btn:hover{background:var(--cx-text);border-color:var(--cx-text-soft);}
.mod-icon{font-size:24px;}
.mod-name{font-size:12px;font-weight:600;text-align:center;}
.mod-badge{font-size:10px;padding:1px 7px;border-radius:10px;font-weight:700;}
.mb-warn{background:#451a03;color:#fcd34d;}
.mb-ok{background:#052e16;color:#86efac;}
.mb-neutral{background:var(--cx-text);color:var(--cx-text-faint);}
.comp-mini{display:flex;flex-direction:column;gap:6px;}
.comp-mini-item{display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--cx-text);border-radius:6px;border:1px solid var(--cx-text);}
.comp-mini-item.crit{border-left:2px solid var(--cx-danger);}
.comp-mini-item.alta{border-left:2px solid var(--cx-warn);}
.comp-mini-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.dot-crit{background:var(--cx-danger);}
.dot-alta{background:var(--cx-warn);}
.dot-norm{background:var(--cx-info);}
.comp-mini-text{font-size:12px;color:var(--cx-border);flex:1;line-height:1.3;}
.comp-mini-meta{font-size:10px;color:var(--cx-text-mute);margin-left:auto;text-align:right;white-space:nowrap;}
.section-hdr{font-size:13px;font-weight:700;color:var(--cx-border-soft);margin-bottom:10px;}
.loading{color:var(--cx-text-mute);font-size:12px;text-align:center;padding:20px;}
.spinner-txt{animation:pulse 1.5s infinite;}
.quick-nav{background:var(--cx-text);border-bottom:1px solid var(--cx-text-soft);padding:8px 20px;display:flex;gap:8px;overflow-x:auto;flex-wrap:nowrap;}
.quick-nav::-webkit-scrollbar{height:3px;}
.quick-nav::-webkit-scrollbar-thumb{background:var(--cx-text-soft);border-radius:2px;}
.qn-btn{display:inline-flex;align-items:center;gap:5px;padding:6px 14px;background:var(--cx-text);border:1px solid var(--cx-text-soft);border-radius:20px;color:var(--cx-border);font-size:12px;font-weight:600;text-decoration:none;white-space:nowrap;transition:.15s;flex-shrink:0;}
.qn-btn:hover{background:var(--cx-text-soft);color:var(--cx-border-soft);border-color:var(--cx-text-soft);}
.qn-btn.primary{background:var(--cx-info);border-color:var(--cx-info);color:#fff;}
.qn-btn.primary:hover{background:#1d4ed8;}
.qn-sep{width:1px;background:var(--cx-text-soft);margin:0 4px;flex-shrink:0;}
</style>
</head>
<body>
<div class="header">
  <div style="display:flex;align-items:center;gap:14px;">
    <span style="width:46px;height:46px;border-radius:10px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;color:var(--cx-primary-text);" aria-label="EOS">
      <svg viewBox="0 0 32 32" width="40" height="40" fill="none" stroke="#6d28d9" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="12" r="3" fill="#6d28d9"/>
        <path d="M 5 19 Q 16 17, 27 19" stroke-width="1.5" stroke-linecap="round" opacity=".55"/>
        <path d="M 5 23 Q 16 21, 27 23" stroke-width="1.5" stroke-linecap="round" opacity=".25"/>
      </svg>
    </span>
    <div>
      <div class="header-logo" style="display:flex;align-items:baseline;gap:8px;">
        <span style="background:linear-gradient(135deg,#a78bfa,#6d28d9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">EOS</span>
        <span style="font-size:10px;color:var(--cx-primary-light);font-weight:600;letter-spacing:1px;text-transform:uppercase;border:1px solid var(--cx-primary-dark);padding:2px 6px;border-radius:4px;">v1.0</span>
      </div>
      <div class="header-sub">by <strong style="color:var(--cx-border)">HHA Group</strong> &nbsp;·&nbsp; Espagiria &nbsp;·&nbsp; ANIMUS Lab</div>
    </div>
  </div>
  <div class="header-right">
    <strong id="fecha-hoy"></strong>
    <span>Panel Central</span>
  </div>
</div>

<div class="quick-nav">
  <a class="qn-btn primary" href="/inventarios">&#x1F4E6; Planta</a>
  <a class="qn-btn" href="/compras">&#x1F6D2; Compras</a>
  <a class="qn-btn" href="/recepcion">&#x1F69A; Recepci&#xF3;n</a>
  <a class="qn-btn" href="/clientes">&#x1F464; Clientes</a>
  <a class="qn-btn" href="/financiero">&#x1F4CA; Financiero</a>
  <a class="qn-btn" href="/gerencia">&#x1F3DB; Gerencia</a>
  <a class="qn-btn" href="/calidad">&#x1F52C; Calidad</a>
  <a class="qn-btn" href="/tecnica">&#x1F527; T&#xE9;cnica</a>
  <a class="qn-btn" href="/rrhh">&#x1F465; RRHH</a>
  <a class="qn-btn" href="/hub-salida">&#x1F9EA; Maquila</a>
  <a class="qn-btn" href="/compromisos">&#x2705; Compromisos</a>
  <a class="qn-btn" href="/solicitudes">&#x1F4DD; Solicitudes</a>
  <a class="qn-btn" href="/contabilidad" style="background:#0f2d1f;border-color:var(--cx-success);color:#4ade80;font-weight:600;">&#x1F4B0; Contabilidad</a>
  <div class="qn-sep"></div>
  <a class="qn-btn" href="/modulos" style="background:#1e3a5f;border-color:var(--cx-info);color:#93c5fd;font-weight:700;">&#x1F4F1; Panel de M&#xF3;dulos</a>
  <div class="qn-sep"></div>
  <a class="qn-btn" href="#" onclick="event.preventDefault();openPwdModal();return false;" style="color:var(--cx-primary-light);border-color:var(--cx-primary-dark);">&#x1F510; Cambiar contraseña</a>
  <a class="qn-btn" href="/logout" style="color:#f87171;border-color:var(--cx-danger);">&#x23CF; Cerrar sesión</a>
</div>

<!-- ─── Modal cambio de contraseña ─── -->
<div id="pwd-modal-bg" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:var(--cx-text);border:1px solid var(--cx-text-soft);border-radius:14px;padding:28px;max-width:420px;width:92%;color:var(--cx-border);font-family:'Segoe UI',sans-serif;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px;">
      <h2 style="font-size:18px;font-weight:700;color:var(--cx-border-soft);margin:0;">&#x1F510; Cambiar contraseña</h2>
      <button onclick="closePwdModal()" style="background:none;border:none;color:var(--cx-text-mute);font-size:22px;cursor:pointer;line-height:1;">×</button>
    </div>
    <div style="font-size:12px;color:var(--cx-text-faint);margin-bottom:18px;">Tu nueva contraseña debe tener mínimo 8 caracteres, al menos una letra y un número.</div>
    <form id="pwd-form" onsubmit="return submitPwdChange(event)" style="display:flex;flex-direction:column;gap:12px;">
      <div>
        <label style="font-size:11px;color:var(--cx-text-faint);font-weight:600;text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:4px;">Contraseña actual</label>
        <input type="password" id="pwd-actual" required autocomplete="current-password" style="background:var(--cx-text);border:1px solid var(--cx-text-soft);color:var(--cx-border);padding:9px 12px;border-radius:8px;font-size:13px;width:100%;font-family:inherit;" />
      </div>
      <div>
        <label style="font-size:11px;color:var(--cx-text-faint);font-weight:600;text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:4px;">Nueva contraseña</label>
        <input type="password" id="pwd-nueva" required minlength="8" maxlength="128" autocomplete="new-password" style="background:var(--cx-text);border:1px solid var(--cx-text-soft);color:var(--cx-border);padding:9px 12px;border-radius:8px;font-size:13px;width:100%;font-family:inherit;" />
      </div>
      <div>
        <label style="font-size:11px;color:var(--cx-text-faint);font-weight:600;text-transform:uppercase;letter-spacing:.05em;display:block;margin-bottom:4px;">Confirmar nueva contraseña</label>
        <input type="password" id="pwd-confirmar" required minlength="8" maxlength="128" autocomplete="new-password" style="background:var(--cx-text);border:1px solid var(--cx-text-soft);color:var(--cx-border);padding:9px 12px;border-radius:8px;font-size:13px;width:100%;font-family:inherit;" />
      </div>
      <div id="pwd-msg" style="font-size:12px;min-height:18px;padding:6px 0;"></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:6px;">
        <button type="button" onclick="closePwdModal()" style="background:transparent;border:1px solid var(--cx-text-soft);color:var(--cx-text-faint);padding:9px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;">Cancelar</button>
        <button type="submit" id="pwd-submit-btn" style="background:linear-gradient(135deg,#7c3aed,#4c1d95);border:none;color:#fff;padding:9px 22px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:700;">Guardar</button>
      </div>
    </form>
  </div>
</div>

<script>
function openPwdModal() {
  document.getElementById('pwd-modal-bg').style.display = 'flex';
  document.getElementById('pwd-actual').value = '';
  document.getElementById('pwd-nueva').value = '';
  document.getElementById('pwd-confirmar').value = '';
  document.getElementById('pwd-msg').textContent = '';
  document.getElementById('pwd-msg').style.color = '';
  setTimeout(() => document.getElementById('pwd-actual').focus(), 50);
}
function closePwdModal() {
  document.getElementById('pwd-modal-bg').style.display = 'none';
}
async function submitPwdChange(ev) {
  ev.preventDefault();
  const actual = document.getElementById('pwd-actual').value;
  const nueva = document.getElementById('pwd-nueva').value;
  const confirmar = document.getElementById('pwd-confirmar').value;
  const msg = document.getElementById('pwd-msg');
  const btn = document.getElementById('pwd-submit-btn');

  msg.style.color = '#fbbf24';
  msg.textContent = 'Validando...';

  if (nueva !== confirmar) {
    msg.style.color = '#f87171';
    msg.textContent = 'La confirmación no coincide.';
    return false;
  }
  if (nueva.length < 8) {
    msg.style.color = '#f87171';
    msg.textContent = 'Mínimo 8 caracteres.';
    return false;
  }
  if (!/[a-zA-Z]/.test(nueva) || !/\\d/.test(nueva)) {
    msg.style.color = '#f87171';
    msg.textContent = 'Debe incluir al menos una letra y un número.';
    return false;
  }

  btn.disabled = true;
  btn.style.opacity = '0.6';
  try {
    const r = await fetch('/api/cambiar-password', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        password_actual: actual,
        password_nueva: nueva,
        password_confirmar: confirmar
      })
    });
    const data = await r.json();
    if (r.ok && data.ok) {
      msg.style.color = '#34d399';
      msg.textContent = '✓ Contraseña actualizada correctamente.';
      setTimeout(closePwdModal, 1500);
    } else {
      msg.style.color = '#f87171';
      msg.textContent = data.error || 'Error desconocido';
    }
  } catch (e) {
    msg.style.color = '#f87171';
    msg.textContent = 'Error de red: ' + e.message;
  } finally {
    btn.disabled = false;
    btn.style.opacity = '';
  }
  return false;
}
// Cerrar modal con Escape o click fuera
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closePwdModal();
});
document.getElementById('pwd-modal-bg').addEventListener('click', e => {
  if (e.target.id === 'pwd-modal-bg') closePwdModal();
});
</script>

<div class="alert-bar" id="alert-bar">
  <span class="spinner-txt" style="font-size:12px;color:var(--cx-text-mute);">Calculando alertas...</span>
</div>

<div class="main">
  <div class="card card-full">
    <div class="card-title" style="font-size:13px;color:var(--cx-border);">&#x1F4F1; Panel de M&#xF3;dulos</div>
    <div class="module-grid" id="mod-grid">
      <a class="mod-btn" href="/inventarios"><span class="mod-icon">&#x1F4E6;</span><span class="mod-name">Planta</span><span class="mod-badge mb-neutral" id="mb-inv">-</span></a>
      <a class="mod-btn" href="/compras"><span class="mod-icon">&#x1F6D2;</span><span class="mod-name">Compras</span><span class="mod-badge mb-neutral" id="mb-comp">-</span></a>
      <a class="mod-btn" href="/recepcion"><span class="mod-icon">&#x1F69A;</span><span class="mod-name">Recepcion</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/clientes"><span class="mod-icon">&#x1F464;</span><span class="mod-name">Clientes</span><span class="mod-badge mb-neutral" id="mb-cli">-</span></a>
      <a class="mod-btn" href="/financiero"><span class="mod-icon">&#x1F4CA;</span><span class="mod-name">Financiero</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/gerencia"><span class="mod-icon">&#x1F3DB;</span><span class="mod-name">Gerencia</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/compromisos"><span class="mod-icon">&#x2705;</span><span class="mod-name">Compromisos</span><span class="mod-badge mb-neutral" id="mb-comp2">-</span></a>
      <a class="mod-btn" href="/hub-salida"><span class="mod-icon">&#x1F9EA;</span><span class="mod-name">Maquila</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/calidad"><span class="mod-icon">&#x1F52C;</span><span class="mod-name">Calidad</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/tecnica"><span class="mod-icon">&#x1F527;</span><span class="mod-name">Técnica</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/rrhh"><span class="mod-icon">&#x1F465;</span><span class="mod-name">RRHH</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/solicitudes"><span class="mod-icon">&#x1F4DD;</span><span class="mod-name">Solicitudes</span><span class="mod-badge mb-ok">activo</span></a>
      <a class="mod-btn" href="/contabilidad"><span class="mod-icon">&#x1F4B0;</span><span class="mod-name">Contabilidad</span><span class="mod-badge mb-ok">activo</span></a>
    </div>
  </div>

  <!-- ALERTAS ACTIVAS -->
  <div class="card">
    <div class="card-title">&#x26A0; Requiere tu decision</div>
    <div id="alertas-list"><div class="loading spinner-txt">Cargando...</div></div>
  </div>

  <!-- PULSO FINANCIERO -->
  <div class="card">
    <div class="card-title">&#x1F4B0; Pulso Financiero</div>
    <div class="kpi-grid" id="kpi-fin">
      <div class="loading spinner-txt" style="grid-column:1/-1;">Cargando...</div>
    </div>
  </div>

  <!-- COMPROMISOS CRITICOS -->
  <div class="card">
    <div class="card-title">&#x1F4CB; Compromisos criticos &amp; vencidos</div>
    <div id="comp-list"><div class="loading spinner-txt">Cargando...</div></div>
    <a href="/compromisos" style="display:block;text-align:center;margin-top:10px;font-size:12px;color:var(--cx-text-mute);text-decoration:none;">Ver todos los compromisos &rarr;</a>
  </div>

</div>

<script>
document.getElementById('fecha-hoy').textContent = new Date().toLocaleDateString('es-CO',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

function fmt(n){ return '$'+parseFloat(n||0).toLocaleString('es-CO',{minimumFractionDigits:0,maximumFractionDigits:0}); }

async function loadAll(){
  try{
    var [ra, rr] = await Promise.all([fetch('/api/hub/alertas'), fetch('/api/hub/resumen')]);
    var alertas = await ra.json();
    var resumen = await rr.json();
    renderAlerts(alertas);
    renderKpis(resumen);
    updateModuleBadges(alertas.resumen, resumen);
  }catch(e){ console.error(e); }
  try{
    var rc = await fetch('/api/compromisos?estado=Todos');
    var dc = await rc.json();
    renderCompromisos(dc.compromisos||[]);
  }catch(e){}
}

function renderAlerts(data){
  var alertas = data.alertas||[];
  var res = data.resumen||{};
  // Update alert bar
  var barHtml = '';
  if(res.critico>0) barHtml += '<div class="al-pill al-crit"><span class="al-pulse"></span>'+res.critico+' urgente'+(res.critico>1?'s':'')+'</div>';
  if(res.atencion>0) barHtml += '<div class="al-pill al-aten"><span class="al-pulse"></span>'+res.atencion+' atencion</div>';
  if(!res.critico && !res.atencion) barHtml = '<div class="al-pill al-ok"><span class="al-pulse"></span>Todo en orden</div>';
  document.getElementById('alert-bar').innerHTML = barHtml;
  // Alertas list
  if(!alertas.length){
    document.getElementById('alertas-list').innerHTML='<div class="loading" style="color:#4ade80;">&#x2705; Sin alertas activas</div>';
    return;
  }
  document.getElementById('alertas-list').innerHTML = alertas.slice(0,8).map(function(a){
    var icon = a.nivel==='critico' ? '&#x1F534;' : '&#x1F7E1;';
    return '<div class="alert-item '+a.nivel+'">'+
      '<span class="al-icon">'+icon+'</span>'+
      '<div class="al-body">'+
        '<div class="al-title">'+a.titulo+'</div>'+
        '<div class="al-detail">'+a.detalle+'</div>'+
        (a.accion?'<a class="al-action" href="'+a.accion+'">Ver &rarr;</a>':'')+
      '</div></div>';
  }).join('');
}

function renderKpis(r){
  var ocs = r.ocs||{};
  var comps = r.compromisos||{};
  document.getElementById('kpi-fin').innerHTML =
    mkKpi('Por autorizar', ocs.por_autorizar+' OCs', fmt(ocs.valor_autorizar||0), ocs.por_autorizar>0?'warn':'')+
    mkKpi('Por pagar', ocs.por_pagar+' OCs', fmt(ocs.valor_pagar||0), ocs.por_pagar>0?'warn':'')+
    mkKpi('Pagado esta semana', '',''+fmt(r.pagado_semana||0), 'good')+
    mkKpi('Stock critico', r.stock_critico+' materiales', 'bajo minimo', r.stock_critico>5?'crit':r.stock_critico>0?'warn':'')+
    mkKpi('Compromisos pendientes', comps.pendientes+' items', comps.vencidos+' vencidos', comps.vencidos>0?'crit':'')+
    mkKpi('Clientes activos', r.clientes||0,'en sistema','');
}

function mkKpi(label,val,sub,cls){
  return '<div class="kpi"><div class="kpi-label">'+label+'</div><div class="kpi-val'+(cls?' '+cls:'')+'" >'+val+'</div><div class="kpi-sub">'+sub+'</div></div>';
}

function renderCompromisos(items){
  var hoy = new Date().toISOString().substring(0,10);
  var urgent = items.filter(function(c){
    return c.estado!=='Completado'&&c.estado!=='Cancelado'&&(c.prioridad==='Critico'||(c.fecha_limite&&c.fecha_limite<hoy));
  }).slice(0,6);
  if(!urgent.length){
    document.getElementById('comp-list').innerHTML='<div class="loading" style="color:#4ade80;">&#x2705; Sin compromisos urgentes</div>';
    return;
  }
  document.getElementById('comp-list').innerHTML = urgent.map(function(c){
    var isVenc = c.fecha_limite && c.fecha_limite < hoy;
    var cls = c.prioridad==='Critico'?'crit':'alta';
    var dotCls = c.prioridad==='Critico'?'dot-crit':'dot-alta';
    return '<div class="comp-mini-item '+cls+'">'+
      '<span class="comp-mini-dot '+dotCls+'"></span>'+
      '<span class="comp-mini-text">'+c.descripcion.substring(0,55)+'</span>'+
      '<span class="comp-mini-meta">'+(isVenc?'<span style="color:#f87171;">VENC</span> ':'')+c.responsable+'<br>'+(c.fecha_limite||'')+'</span>'+
    '</div>';
  }).join('');
}

function updateModuleBadges(alRes, r){
  var compBadge = document.getElementById('mb-comp');
  if(compBadge){
    var cnt = (r.ocs||{}).por_autorizar||0;
    compBadge.textContent = cnt>0 ? cnt+' pendiente'+(cnt>1?'s':'') : 'ok';
    compBadge.className = 'mod-badge '+(cnt>0?'mb-warn':'mb-ok');
  }
  var cliBadge = document.getElementById('mb-cli');
  if(cliBadge){ cliBadge.textContent = r.clientes+' activos'; }
  var comp2 = document.getElementById('mb-comp2');
  if(comp2){
    var cv = (r.compromisos||{}).vencidos||0;
    comp2.textContent = cv>0?cv+' vencidos':'ok';
    comp2.className = 'mod-badge '+(cv>0?'mb-warn':'mb-ok');
  }
}

loadAll();
setInterval(loadAll, 60000);
</script>

<footer style="padding:18px 20px;border-top:1px solid var(--cx-text-soft);margin-top:24px;text-align:center;font-size:11px;color:var(--cx-text-mute);background:var(--cx-text);">
  <div style="display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;">
    <span style="font-weight:700;background:linear-gradient(135deg,#a78bfa,#6d28d9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:0.3px;font-size:13px;">EOS</span>
    <span style="font-size:9px;color:var(--cx-primary-light);font-weight:700;letter-spacing:1px;text-transform:uppercase;border:1px solid var(--cx-primary-dark);padding:1px 5px;border-radius:3px;">v1.0</span>
  </div>
  <div style="margin-top:6px;font-style:italic;color:var(--cx-text-faint);">Todo el holding, al frente</div>
  <div style="margin-top:10px;letter-spacing:1px;text-transform:uppercase;font-size:10px;">Desarrollado por <strong style="color:var(--cx-border)">HHA Group</strong></div>
  <div style="margin-top:6px;color:var(--cx-text-soft);font-size:10px;">&copy; 2026 HHA Group S.A.S. &middot; Todos los derechos reservados</div>
</footer>

</body>
</html>"""
