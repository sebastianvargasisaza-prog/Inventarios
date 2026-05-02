"""Template HTML de /mi-bandeja · centro de comando del CEO.

Una sola pantalla con TODO lo pendiente cross-módulo. Auto-refresh 60s.
"""

BANDEJA_CEO_HTML = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mi Bandeja · CEO</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
    background: #f8fafc; color: #1e293b; min-height: 100vh; padding: 20px;
  }
  .container { max-width: 1100px; margin: 0 auto; }
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #e2e8f0;
  }
  .topbar h1 { font-size: 22px; margin: 0; color: #0f172a; }
  .meta { font-size: 12px; color: #64748b; }
  .nav a { color: #2B7A78; text-decoration: none; margin-right: 14px; font-size: 12px; }
  .nav a:hover { text-decoration: underline; }
  .summary {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px; margin-bottom: 18px;
  }
  .pill {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 14px 16px; text-align: center;
  }
  .pill .num { font-size: 28px; font-weight: 700; line-height: 1; }
  .pill .lbl { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
                color: #64748b; margin-top: 6px; }
  .pill.critical { border-left: 4px solid #dc2626; }
  .pill.critical .num { color: #dc2626; }
  .pill.high { border-left: 4px solid #f59e0b; }
  .pill.high .num { color: #d97706; }
  .pill.medium { border-left: 4px solid #0ea5e9; }
  .pill.medium .num { color: #0284c7; }
  .pill.total .num { color: #0f172a; }

  .filters {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px;
  }
  .filter-btn {
    background: #fff; border: 1px solid #cbd5e1; border-radius: 18px;
    padding: 6px 14px; font-size: 12px; font-weight: 600;
    cursor: pointer; color: #475569;
  }
  .filter-btn.active { background: #1e293b; border-color: #1e293b; color: #fff; }
  .filter-btn:hover { background: #f1f5f9; }
  .filter-btn.active:hover { background: #0f172a; }

  .group { margin-bottom: 22px; }
  .group-title {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
    color: #64748b; margin-bottom: 8px; padding-left: 4px; font-weight: 700;
  }
  .item {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 12px 14px; margin-bottom: 8px;
    display: flex; gap: 12px; align-items: flex-start;
    transition: transform 0.1s ease, box-shadow 0.1s ease;
  }
  .item:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); transform: translateY(-1px); }
  .item.critical { border-left: 4px solid #dc2626; }
  .item.high { border-left: 4px solid #f59e0b; }
  .item.medium { border-left: 4px solid #0ea5e9; }
  .item-icon {
    font-size: 18px; min-width: 22px; text-align: center;
  }
  .item-body { flex: 1; min-width: 0; }
  .item-title {
    font-weight: 700; color: #0f172a; font-size: 13px; line-height: 1.4;
    margin-bottom: 3px;
  }
  .item-desc { font-size: 12px; color: #64748b; line-height: 1.5; }
  .item-meta {
    display: flex; gap: 10px; align-items: center;
    margin-top: 6px; font-size: 11px;
  }
  .badge-modulo {
    background: #f1f5f9; color: #475569; padding: 2px 8px;
    border-radius: 4px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.3px; font-size: 10px;
  }
  .item-action {
    background: #1e293b; color: #fff; padding: 6px 12px;
    border-radius: 6px; text-decoration: none; font-size: 12px;
    font-weight: 600; white-space: nowrap; align-self: center;
  }
  .item-action:hover { background: #0f172a; }

  .empty {
    background: #f0fdf4; border-left: 4px solid #16a34a;
    padding: 24px; border-radius: 8px; text-align: center; color: #166534;
    font-size: 14px;
  }
  .spinner {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid #cbd5e1; border-top-color: #1e293b;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-right: 6px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  button.refresh {
    background: #1e293b; color: #fff; border: none; padding: 6px 14px;
    border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px;
  }
  button.refresh:hover { background: #0f172a; }
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <div>
      <h1>📋 Mi Bandeja · CEO</h1>
      <div class="nav">
        <a href="/admin/system-health">System Health</a>
        <a href="/financiero">Financiero</a>
        <a href="/aseguramiento">Aseguramiento</a>
        <a href="/compras">Compras</a>
      </div>
    </div>
    <div style="text-align:right">
      <div class="meta">
        Actualizado: <span id="ts">—</span>
        &nbsp; <button class="refresh" onclick="loadBandeja()">↻ Refresh</button>
      </div>
    </div>
  </div>

  <div class="summary" id="summary">
    <div class="pill"><div class="num">—</div><div class="lbl">cargando…</div></div>
  </div>

  <div class="filters" id="filters">
    <button class="filter-btn active" data-filter="all" onclick="setFilter('all',this)">Todo</button>
    <button class="filter-btn" data-filter="critical" onclick="setFilter('critical',this)">🔴 Críticos</button>
    <button class="filter-btn" data-filter="high" onclick="setFilter('high',this)">🟡 Alta</button>
    <button class="filter-btn" data-filter="medium" onclick="setFilter('medium',this)">🟢 Media</button>
  </div>

  <div id="content">
    <div class="empty"><span class="spinner"></span> Cargando bandeja…</div>
  </div>
</div>

<script>
var _allItems = [];
var _currentFilter = 'all';

var SEVERIDAD_LABEL = {
  critical: '🔴 Atención HOY',
  high: '🟡 Esta semana',
  medium: '🟢 Cuando puedas',
};
var ICON_BY_MODULO = {
  recalls: '🚨', compliance: '❌', planta: '🏭',
  compras: '🛒', aseguramiento: '📋', tecnica: '🏛️',
};

function _esc(s){
  return String(s||'').replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function setFilter(f, el){
  _currentFilter = f;
  document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.remove('active');});
  if(el) el.classList.add('active');
  render();
}

function render(){
  var items = _allItems;
  if(_currentFilter !== 'all'){
    items = items.filter(function(it){return it.severidad === _currentFilter;});
  }
  var content = document.getElementById('content');
  if(!items.length){
    content.innerHTML = '<div class="empty">✅ Sin pendientes en esta categoría · seguí así</div>';
    return;
  }
  var groups = {critical: [], high: [], medium: []};
  items.forEach(function(it){
    if(groups[it.severidad]) groups[it.severidad].push(it);
  });
  var html = '';
  ['critical','high','medium'].forEach(function(sev){
    if(!groups[sev].length) return;
    html += '<div class="group">';
    html += '<div class="group-title">'+(SEVERIDAD_LABEL[sev]||sev)+' · '+groups[sev].length+'</div>';
    groups[sev].forEach(function(it){
      var icon = ICON_BY_MODULO[it.modulo] || '·';
      html += '<div class="item '+sev+'">'
        +'<div class="item-icon">'+icon+'</div>'
        +'<div class="item-body">'
          +'<div class="item-title">'+_esc(it.titulo)+'</div>'
          +'<div class="item-desc">'+_esc(it.descripcion)+'</div>'
          +'<div class="item-meta">'
            +'<span class="badge-modulo">'+_esc(it.modulo)+'</span>'
            +(it.edad_dias !== null && it.edad_dias !== undefined
              ? '<span style="color:#94a3b8">⏱ '+it.edad_dias+'d</span>'
              : '')
          +'</div>'
        +'</div>'
        +'<a href="'+_esc(it.link)+'" class="item-action">Abrir →</a>'
        +'</div>';
    });
    html += '</div>';
  });
  content.innerHTML = html;
}

function renderSummary(d){
  var counts = d.counts || {};
  var total = d.total || 0;
  var html = '';
  html += '<div class="pill total"><div class="num">'+total+'</div><div class="lbl">Total pendientes</div></div>';
  html += '<div class="pill critical"><div class="num">'+(counts.critical||0)+'</div><div class="lbl">🔴 Críticos</div></div>';
  html += '<div class="pill high"><div class="num">'+(counts.high||0)+'</div><div class="lbl">🟡 Alta</div></div>';
  html += '<div class="pill medium"><div class="num">'+(counts.medium||0)+'</div><div class="lbl">🟢 Media</div></div>';
  document.getElementById('summary').innerHTML = html;

  // Title de la pestaña con count crítico
  if(counts.critical > 0){
    document.title = '🔴 ('+counts.critical+') Mi Bandeja · CEO';
  }else if(total > 0){
    document.title = '🟡 ('+total+') Mi Bandeja · CEO';
  }else{
    document.title = '✅ Mi Bandeja · CEO';
  }
}

async function loadBandeja(){
  var content = document.getElementById('content');
  content.innerHTML = '<div class="empty"><span class="spinner"></span> Cargando…</div>';
  try{
    var r = await fetch('/api/bandeja-ceo');
    if(!r.ok){
      var err = await r.text();
      content.innerHTML = '<div class="empty" style="background:#fef2f2;border-left-color:#dc2626;color:#991b1b">Error '+r.status+'</div>';
      return;
    }
    var d = await r.json();
    document.getElementById('ts').textContent = (d.timestamp||'').slice(0,19).replace('T',' ')+' UTC';
    _allItems = d.items || [];
    renderSummary(d);
    render();
  }catch(e){
    content.innerHTML = '<div class="empty" style="background:#fef2f2;border-left-color:#dc2626;color:#991b1b">Error red: '+_esc(e.message)+'</div>';
  }
}

loadBandeja();
setInterval(loadBandeja, 60000);
</script>
</body>
</html>'''
